"""Repository-root discovery.

All project paths are resolved relative to the repository root, which is located by walking up
from this file until a directory containing both ``pyproject.toml`` and ``config/`` is found.
Set the environment variable ``SRL_PROJECT_ROOT`` to override (e.g., in a replication container).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def project_root() -> Path:
    """Return the absolute path of the repository root."""
    override = os.environ.get("SRL_PROJECT_ROOT")
    if override:
        return Path(override).resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "config").is_dir():
            return parent
    raise RuntimeError(
        "Could not locate the repository root (pyproject.toml + config/). "
        "Set SRL_PROJECT_ROOT explicitly."
    )


def relpath(path: str | Path) -> str:
    """Return ``path`` relative to the repository root in POSIX form (for logs and manifests)."""
    path = Path(path).resolve()
    try:
        return path.relative_to(project_root()).as_posix()
    except ValueError:
        return path.as_posix()
