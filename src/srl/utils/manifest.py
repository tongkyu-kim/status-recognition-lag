"""Raw-data manifest: provenance and immutability checks.

Every file under ``data/raw/<source_id>/<YYYY-MM-DD>/`` is registered in ``data/raw_manifest.csv``
with its SHA-256 checksum. :func:`verify_manifest` detects raw files that were modified, removed,
or added without registration. The manifest itself is tracked in Git; raw files are not.
"""

from __future__ import annotations

import logging
import os
import re
import stat
from datetime import date
from pathlib import Path

import pandas as pd

from srl.utils.config import get_path, load_config
from srl.utils.io import sha256_file
from srl.utils.paths import project_root, relpath

logger = logging.getLogger(__name__)

MANIFEST_COLUMNS = [
    "relative_path",
    "source_id",
    "retrieved_on",
    "sha256",
    "size_bytes",
    "registered_on",
    "notes",
]
_IGNORED_NAMES = {".gitkeep", "README.md", ".DS_Store", "Thumbs.db", "desktop.ini"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ManifestError(RuntimeError):
    """Raw files changed, disappeared, or were never registered."""


def load_manifest() -> pd.DataFrame:
    path = get_path("data.raw_manifest")
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=MANIFEST_COLUMNS)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _save_manifest(df: pd.DataFrame) -> None:
    path = get_path("data.raw_manifest")
    df = df[MANIFEST_COLUMNS].sort_values("relative_path").reset_index(drop=True)
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def scan_raw_files() -> list[Path]:
    """Return all raw data files (excluding placeholders such as .gitkeep / README.md)."""
    raw = get_path("data.raw")
    return sorted(p for p in raw.rglob("*") if p.is_file() and p.name not in _IGNORED_NAMES)


def _parse_layout(path: Path) -> tuple[str, str]:
    """Infer ``(source_id, retrieved_on)`` from data/raw/<source_id>/<YYYY-MM-DD>/..."""
    parts = path.relative_to(get_path("data.raw")).parts
    source_id = parts[0] if len(parts) > 1 else ""
    retrieved_on = parts[1] if len(parts) > 2 and _DATE_RE.match(parts[1]) else ""
    return source_id, retrieved_on


def register_new_files(*, notes: str = "", lock: bool = False) -> pd.DataFrame:
    """Add unregistered raw files to the manifest; return the newly registered rows.

    Files that do not follow the ``<source_id>/<YYYY-MM-DD>/`` layout, or whose source_id is not
    in ``config/sources.yaml``, are still registered but logged as warnings.
    """
    manifest = load_manifest()
    known = set(manifest["relative_path"])
    source_ids = set(load_config("sources").get("sources", {}))
    rows = []
    for path in scan_raw_files():
        rel = relpath(path)
        if rel in known:
            continue
        source_id, retrieved_on = _parse_layout(path)
        if source_id not in source_ids:
            logger.warning("%s: source_id %r not in config/sources.yaml", rel, source_id)
        if not retrieved_on:
            logger.warning("%s: no YYYY-MM-DD retrieval folder in path", rel)
        rows.append(
            {
                "relative_path": rel,
                "source_id": source_id,
                "retrieved_on": retrieved_on,
                "sha256": sha256_file(path),
                "size_bytes": str(path.stat().st_size),
                "registered_on": date.today().isoformat(),
                "notes": notes,
            }
        )
        if lock:
            os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    new = pd.DataFrame(rows, columns=MANIFEST_COLUMNS)
    if not new.empty:
        _save_manifest(pd.concat([manifest, new], ignore_index=True))
    logger.info("Registered %d new raw file(s)", len(new))
    return new


def verify_manifest() -> pd.DataFrame:
    """Compare raw files on disk with the manifest.

    Returns one row per file with ``status`` in {ok, modified, missing, unregistered}.
    """
    manifest = load_manifest()
    on_disk = {relpath(p): p for p in scan_raw_files()}
    records = []
    for row in manifest.itertuples(index=False):
        path = on_disk.pop(row.relative_path, None)
        if path is None:
            status = "missing"
        elif sha256_file(path) != row.sha256:
            status = "modified"
        else:
            status = "ok"
        records.append({"relative_path": row.relative_path, "status": status})
    records += [{"relative_path": rel, "status": "unregistered"} for rel in sorted(on_disk)]
    report = pd.DataFrame(records, columns=["relative_path", "status"])
    logger.info("Raw manifest check (root=%s): %s", project_root().name,
                report["status"].value_counts().to_dict() if not report.empty else "no raw files")
    return report
