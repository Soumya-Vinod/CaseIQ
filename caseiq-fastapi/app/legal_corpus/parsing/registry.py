from __future__ import annotations

from .base import ActParser
from .gazette_parser import GazetteParser
from .legacy_parser import LegacyActParser

PARSERS: dict[str, ActParser] = {
    "BNS": GazetteParser(),
    # Re-sourced 2026-08-09 (the previous file was a withdrawn Bill, see
    # docs/incidents/2026-08-09-withdrawn-bns-bill-ingested.md). The genuine
    # Act No. 45/2023 India Code print has no line-number gutter -- it parses
    # cleanly with the same GazetteParser as BNSS/BSA at default x_tolerance.
    "BNSS": GazetteParser(),
    "BSA": GazetteParser(x_tolerance=1),  # this file's embedded font drops
    # inter-word spaces at pdfplumber's default x_tolerance=3.
    "IPC": LegacyActParser(),
    "CrPC": LegacyActParser(),
}
