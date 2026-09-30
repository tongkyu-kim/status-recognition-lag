"""Deterministic figure export to ``outputs/figures``."""

from __future__ import annotations

from pathlib import Path

from srl.utils.config import get_path


def save_figure(fig, name: str, formats: tuple[str, ...] = ("pdf", "png"), *,
                dpi: int = 300) -> list[Path]:
    """Save ``fig`` as ``outputs/figures/<name>.<fmt>`` with reproducible metadata.

    PDF creation dates are stripped so that re-running the pipeline yields identical files.
    """
    out_dir = get_path("outputs.figures", mkdir=True)
    paths = []
    for fmt in formats:
        path = out_dir / f"{name}.{fmt}"
        metadata = {"CreationDate": None} if fmt == "pdf" else None
        fig.savefig(path, dpi=dpi, bbox_inches="tight", metadata=metadata)
        paths.append(path)
    return paths
