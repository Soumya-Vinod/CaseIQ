"""Restore-drill item 4: does the re-download path in documents/provenance.json
actually work, checked by using it -- not assumed from the recorded hashes.

Two separate things are verified, for different reasons:

1. Every one of the 5 tracked local PDFs' sha256 matches provenance.json's
   recorded source_sha256 -- confirms the files this repo now ships (see
   docs/deployment.md, "The repo is public") are exactly the verified copies,
   not something that drifted.

2. For the 3 acts that HAVE a recorded source_url (BNS, IPC, CrPC -- BNSS and
   BSA have source_url: null, a real gap found while scoping this, not a bug
   in this script), a FRESH download is made from that URL and its sha256 is
   checked against the same recorded value. This is the actual claim the
   corpus's "rebuildable from source" story depends on for those 3 acts: that
   indiacode.nic.in still serves byte-identical files years later. BNSS/BSA
   have no such fallback at all -- for those two, the tracked local file IS
   the only source of truth, which is exactly the argument for tracking all
   five rather than relying on re-download for any of them.

Usage: python -m scripts.verify_pdf_provenance
Exits non-zero if any check fails.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "documents"
PROVENANCE_PATH = DOCS_DIR / "provenance.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))["acts"]
    failures: list[str] = []

    print("=== 1. Tracked local file integrity (all 5 acts) ===")
    for act, rec in provenance.items():
        path = DOCS_DIR / rec["filename"]
        if not path.exists():
            failures.append(f"{act}: tracked file missing at {path}")
            print(f"  {act}: MISSING ({path})")
            continue
        actual = _sha256(path.read_bytes())
        expected = rec["source_sha256"]
        ok = actual == expected
        print(f"  {act}: {'MATCH' if ok else 'MISMATCH'} ({path.name})")
        if not ok:
            failures.append(f"{act}: local file sha256 {actual} != provenance.json {expected}")

    print("\n=== 2. Fresh re-download from source_url, sha256-verified (URL-bearing acts only) ===")
    for act, rec in provenance.items():
        url_field = rec.get("source_url") or {}
        url = url_field.get("value") if isinstance(url_field, dict) else None
        if not url:
            print(f"  {act}: SKIPPED -- no source_url recorded in provenance.json "
                  f"(only the tracked local file exists for this act)")
            continue
        print(f"  {act}: downloading {url} ...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CaseIQ-provenance-check/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
        except Exception as e:  # noqa: BLE001 -- report exactly what failed, network errors included
            failures.append(f"{act}: download of {url} failed -- {e!r}")
            print(f"    DOWNLOAD FAILED: {e!r}")
            continue
        actual = _sha256(data)
        expected = rec["source_sha256"]
        ok = actual == expected
        print(f"    {'MATCH' if ok else 'MISMATCH'} -- {len(data)} bytes, sha256 {actual[:16]}...")
        if not ok:
            failures.append(f"{act}: fresh download sha256 {actual} != provenance.json {expected}")

    print()
    if failures:
        print(f"FAILED: {len(failures)} problem(s)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
