"""Provenance manifest guard (checklist item B4).

Reads documents/provenance.json and refuses to let ingestion proceed for any
act whose recorded document_type is not "act". This exists because BNS_2023.pdf
was, until 2026-08-09, a withdrawn Bill silently ingested as if it were law --
see docs/incidents/2026-08-09-withdrawn-bns-bill-ingested.md. A parser fix does
not catch that class of error; only checking what the document *is* does.

This module intentionally does no PDF parsing. It is a pre-flight check that
ingest_sections.py calls before handing a path to any format-specific parser.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

MANIFEST_PATH = Path(__file__).resolve().parent.parent.parent / "documents" / "provenance.json"


class ProvenanceError(RuntimeError):
    """Raised when a document's recorded provenance forbids ingestion."""


def load_manifest() -> dict:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)["acts"]


def assert_ingestable(act: str, pdf_path: str) -> dict:
    """Raise ProvenanceError unless `act` is manifested as document_type == "act"
    and its recorded sha256 (if any) matches the file on disk. Returns the
    manifest entry on success.
    """
    manifest = load_manifest()
    entry = manifest.get(act)
    if entry is None:
        raise ProvenanceError(
            f"{act}: no provenance record in {MANIFEST_PATH}. "
            f"Add one before ingesting -- undocumented source documents are not ingestable."
        )

    doc_type = (entry.get("document_type") or {}).get("value")
    if doc_type != "act":
        raise ProvenanceError(
            f"{act}: document_type is {doc_type!r}, not 'act' -- refusing to ingest. "
            f"({pdf_path} must be a notified/enacted Act, not a Bill, draft, or other "
            f"non-enacted instrument. See {MANIFEST_PATH}.)"
        )
    # document_type == "act" is required to ingest regardless of its own verified flag --
    # an *unverified* "act" is allowed through (flagged for follow-up elsewhere), but a
    # *verified* "bill" is still blocked. Only the value gates ingestion.

    recorded_sha = entry.get("source_sha256")
    if recorded_sha:
        actual_sha = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
        if actual_sha != recorded_sha:
            raise ProvenanceError(
                f"{act}: {pdf_path} sha256 ({actual_sha}) does not match the manifest "
                f"({recorded_sha}). The file on disk has changed since it was provenanced -- "
                f"re-verify and update {MANIFEST_PATH} before ingesting."
            )

    return entry


def get_highest_section_number(act: str) -> int | None:
    """The manifest's recorded highest section NUMBER for `act` (e.g. IPC's
    last section is 511), or None if not yet recorded. This is NOT a count of
    sections -- a 165-year-old Act with lettered insertions (124A, 498A, ...)
    and repealed ranges has more distinct entries than its highest number, and
    fewer than its highest number once repeals are excluded. It's used only as
    an informational sanity check in the validation report (does the highest
    accepted number roughly match what the document itself claims as its last
    section?), never as the primary coverage gate -- that's
    parsing/toc.py's expected_section_numbers, a set derived from the
    document's own table of contents.
    """
    entry = load_manifest().get(act) or {}
    return entry.get("highest_section_number")


if __name__ == "__main__":
    # Quick manual audit: print document_type / act_number / content_as_on for every
    # manifested act, and flag any field marked verified:false.
    for act, entry in load_manifest().items():
        doc_type = entry.get("document_type") or {}
        flag = "OK" if doc_type.get("value") == "act" else "BLOCKED"
        unverified = sorted(
            k for k, v in entry.items()
            if isinstance(v, dict) and "verified" in v and not v["verified"]
        )
        print(
            f"{act:6s} [{flag:7s}] type={doc_type.get('value')!r} "
            f"act_no={(entry.get('act_number') or {}).get('value')!r} "
            f"content_as_on={(entry.get('content_as_on') or {}).get('value')!r} "
            f"file={entry.get('filename')} "
            f"unverified_fields={unverified or 'none'}"
        )
