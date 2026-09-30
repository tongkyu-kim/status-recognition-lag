"""Table I/O with a hard guard against writing into ``data/raw``.

Raw data are immutable: every derived table goes to ``data/interim`` or ``data/processed`` (or
``outputs``). :func:`write_table` refuses any destination inside the raw directory.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from srl.utils.config import get_path
from srl.utils.paths import relpath

logger = logging.getLogger(__name__)


class RawDataWriteError(PermissionError):
    """Attempt to write into the immutable raw-data directory."""


class MissingInputError(FileNotFoundError):
    """A pipeline step's required input does not exist yet."""


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def assert_not_raw(path: str | Path) -> None:
    """Raise :class:`RawDataWriteError` if ``path`` lies inside ``data/raw``."""
    if _is_within(Path(path), get_path("data.raw")):
        raise RawDataWriteError(
            f"Refusing to write to {relpath(path)}: data/raw is immutable. "
            "Write derived data to data/interim or data/processed."
        )


def write_table(df: pd.DataFrame, path: str | Path, *, index: bool = False) -> Path:
    """Write a DataFrame as ``.parquet`` or ``.csv`` (UTF-8), creating parent directories."""
    path = Path(path)
    assert_not_raw(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        df.to_parquet(path, index=index)
    elif suffix == ".csv":
        df.to_csv(path, index=index, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported output format: {suffix} (use .parquet or .csv)")
    logger.info("Wrote %d rows x %d cols -> %s", len(df), df.shape[1], relpath(path))
    return path


def read_table(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read ``.parquet``, ``.csv`` or ``.xlsx``; raise :class:`MissingInputError` if absent."""
    path = Path(path)
    if not path.exists():
        raise MissingInputError(f"Input not found: {relpath(path)}")
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path, **kwargs)
    if suffix == ".csv":
        return pd.read_csv(path, **kwargs)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, **kwargs)
    raise ValueError(f"Unsupported input format: {suffix}")


def require_inputs(paths: Iterable[str | Path], hint: str = "") -> None:
    """Raise :class:`MissingInputError` listing every path in ``paths`` that does not exist."""
    missing = [relpath(p) for p in paths if not Path(p).exists()]
    if missing:
        msg = "Missing required input(s): " + ", ".join(missing)
        raise MissingInputError(f"{msg}. {hint}".strip())


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
