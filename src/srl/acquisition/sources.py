"""Source registry built from ``config/sources.yaml`` and helpers to locate/read raw files."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from srl.utils.config import get_path, load_config
from srl.utils.io import MissingInputError, read_table
from srl.utils.paths import relpath

logger = logging.getLogger(__name__)

SIDECAR_NAMES = {"metadata.csv", "README.md", ".gitkeep"}


@dataclass(frozen=True)
class Source:
    source_id: str
    name: str
    category: str
    status: str
    access: str | None = None
    url: str | None = None
    licence: str | None = None
    notes: str = ""
    reader: dict[str, Any] | None = None
    column_map: dict[str, str] | None = field(default=None)


def load_sources() -> dict[str, Source]:
    cfg = load_config("sources").get("sources", {})
    return {
        sid: Source(
            source_id=sid,
            name=spec["name"],
            category=spec["category"],
            status=spec["status"],
            access=spec.get("access"),
            url=spec.get("url"),
            licence=spec.get("licence"),
            notes=spec.get("notes", "") or "",
            reader=spec.get("reader"),
            column_map=spec.get("column_map"),
        )
        for sid, spec in cfg.items()
    }


def sources_by_category(category: str) -> list[Source]:
    return [s for s in load_sources().values() if s.category == category]


def sources_table() -> pd.DataFrame:
    """Overview of all configured sources (for logs and docs)."""
    return pd.DataFrame(
        [
            {"source_id": s.source_id, "category": s.category, "status": s.status,
             "reader_configured": s.reader is not None,
             "column_map_configured": s.column_map is not None,
             "n_raw_files": len(raw_files(s.source_id))}
            for s in load_sources().values()
        ]
    )


def raw_source_dir(source_id: str) -> Path:
    return get_path("data.raw") / source_id


def raw_files(source_id: str) -> list[Path]:
    """Raw data files for a source (sidecar metadata files excluded)."""
    root = raw_source_dir(source_id)
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and p.name not in SIDECAR_NAMES)


def read_raw_source(source: Source) -> pd.DataFrame:
    """Read and concatenate all raw files of a tabular source using its configured ``reader``.

    Adds ``_raw_file`` with the repository-relative path of each row's file for provenance.
    """
    files = raw_files(source.source_id)
    if not files:
        raise MissingInputError(
            f"No raw files for source '{source.source_id}' under "
            f"{relpath(raw_source_dir(source.source_id))}/<YYYY-MM-DD>/"
        )
    if not source.reader:
        raise NotImplementedError(
            f"Source '{source.source_id}': set `reader` in config/sources.yaml after inspecting "
            "the raw files (format, encoding, header rows)."
        )
    reader = dict(source.reader)
    fmt = reader.pop("format", None)
    frames = []
    for path in files:
        if fmt and path.suffix.lower().lstrip(".") != fmt:
            logger.warning("Skipping %s (expected .%s)", relpath(path), fmt)
            continue
        frames.append(read_table(path, **reader).assign(_raw_file=relpath(path)))
    if not frames:
        raise MissingInputError(f"No readable .{fmt} files for source '{source.source_id}'")
    return pd.concat(frames, ignore_index=True)
