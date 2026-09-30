"""Document metadata schema for the government-text corpus.

Deposit convention (see data/README.md): each ``data/raw/<source_id>/<YYYY-MM-DD>/`` folder of
text files carries a ``metadata.csv`` sidecar with one row per document:

    doc_id        unique within source (stable identifier, e.g., the release number)
    file          file name relative to the metadata.csv folder
    title         document title as published
    date          publication date (YYYY-MM-DD)
    institution   issuing body (e.g., "MOFA"); keep a crosswalk for renamed ministries
    doc_type      e.g., press_release | speech | joint_statement | white_paper | minutes
    language      optional (ko | en); detected automatically if missing
    original_url  optional; record only the URL the file was actually obtained from
    notes         optional
"""

from __future__ import annotations

import pandas as pd

from srl.utils.validation import ValidationError, check_unique_keys, require_columns

SIDECAR_REQUIRED = ["doc_id", "file", "title", "date", "institution", "doc_type"]
SIDECAR_OPTIONAL = ["language", "original_url", "notes"]

DOCUMENT_COLUMNS = [
    "doc_uid", "source_id", "doc_id", "title", "date", "year", "institution", "doc_type",
    "language", "original_url", "raw_path", "sha256", "n_chars", "text",
]
DOC_TYPES = {"press_release", "speech", "joint_statement", "white_paper", "minutes", "briefing",
             "other"}


def validate_sidecar(meta: pd.DataFrame, name: str) -> pd.DataFrame:
    """Check a ``metadata.csv`` sidecar and fill optional columns."""
    require_columns(meta, SIDECAR_REQUIRED, name)
    check_unique_keys(meta, ["doc_id"], name)
    meta = meta.copy()
    for col in SIDECAR_OPTIONAL:
        if col not in meta.columns:
            meta[col] = pd.NA
    dates = pd.to_datetime(meta["date"], format="%Y-%m-%d", errors="coerce")
    if dates.isna().any():
        bad = meta.loc[dates.isna(), "doc_id"].head(5).tolist()
        raise ValidationError(f"{name}: unparseable dates (expected YYYY-MM-DD) for doc_id {bad}")
    unknown_types = set(meta["doc_type"].dropna()) - DOC_TYPES
    if unknown_types:
        raise ValidationError(f"{name}: unknown doc_type values {sorted(unknown_types)}; "
                              f"allowed: {sorted(DOC_TYPES)}")
    meta["date"] = dates.dt.strftime("%Y-%m-%d")
    return meta
