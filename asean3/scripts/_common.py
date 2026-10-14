"""Shared paths and constants for the ASEAN+3 industrial-homogeneity study (asean3/).

Raw files are written through the parent project's write-once helper
(srl.acquisition.fetch.save_raw -> data/raw/<source_id>/<date>/). Everything this study derives is
written under asean3/data/ and asean3/outputs/, never into the parent project's derived folders.
"""

from __future__ import annotations

import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parent
try:
    import srl  # noqa: F401
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT / "src"))

RAW = ROOT / "data" / "raw"
INTERIM = STUDY / "data" / "interim"
PROCESSED = STUDY / "data" / "processed"
OUT = STUDY / "outputs"
for p in (INTERIM, PROCESSED, OUT / "tables", OUT / "figures", OUT / "models", OUT / "diagnostics",
          OUT / "coding", OUT / "reports"):
    p.mkdir(parents=True, exist_ok=True)

SEED = 20261014

# ASEAN+3 universe (contemporary configuration: 11 AMS incl. Timor-Leste + CHN, JPN, KOR).
ASEAN3 = ["BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "TLS", "VNM", "CHN", "JPN", "KOR"]
PLUS3 = ["CHN", "JPN", "KOR"]
M49 = {"KOR": 410, "BRN": 96, "KHM": 116, "IDN": 360, "LAO": 418, "MYS": 458, "MMR": 104, "PHL": 608,
       "SGP": 702, "THA": 764, "TLS": 626, "VNM": 704, "CHN": 156, "JPN": 392}

# Historical membership (verified dates; see asean3/docs/membership.md for sources).
ASEAN_ACCESSION = {"IDN": 1967, "MYS": 1967, "PHL": 1967, "SGP": 1967, "THA": 1967, "BRN": 1984,
                   "VNM": 1995, "LAO": 1997, "MMR": 1997, "KHM": 1999, "TLS": 2025}
# WTO membership dates verified in data/interim/prelim/event_transitions.csv (parent project).
WTO_ACCESSION = {"BRN": "1995-01-01", "IDN": "1995-01-01", "KOR": "1995-01-01", "MYS": "1995-01-01",
                 "MMR": "1995-01-01", "PHL": "1995-01-01", "SGP": "1995-01-01", "THA": "1995-01-01",
                 "JPN": "1995-01-01", "KHM": "2004-10-13", "CHN": "2001-12-11", "VNM": "2007-01-11",
                 "LAO": "2013-02-02", "TLS": "2024-08-30"}
# Timor-Leste: independence restored 20 May 2002 (UN member 27 Sep 2002).
STATEHOOD_FROM = {"TLS": 2002}
