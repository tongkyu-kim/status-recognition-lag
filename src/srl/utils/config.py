"""Configuration loading.

Configuration lives in ``config/*.yaml``. Paths in ``config/paths.yaml`` must be relative to the
repository root; :func:`get_path` enforces this so that no absolute, machine-specific path can
enter the pipeline.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import yaml

from srl.utils.paths import project_root


class ConfigError(RuntimeError):
    """A configuration file is missing, malformed, or a required setting is still undecided."""


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file; relative paths are resolved against the repository root."""
    path = Path(path)
    if not path.is_absolute():
        path = project_root() / path
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or {}


def load_config(name: str) -> dict[str, Any]:
    """Load ``config/<name>.yaml`` (e.g., ``load_config("countries")``)."""
    return load_yaml(Path("config") / f"{name}.yaml")


def _lookup(tree: dict[str, Any], dotted_key: str) -> Any:
    node: Any = tree
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigError(f"Key '{dotted_key}' not found in config/paths.yaml")
        node = node[part]
    return node


def _is_absolute(rel: str) -> bool:
    return PurePosixPath(rel).is_absolute() or PureWindowsPath(rel).is_absolute() or ":" in rel


def get_path(key: str, *, mkdir: bool = False) -> Path:
    """Resolve a dotted key from ``config/paths.yaml`` to an absolute path.

    Parameters
    ----------
    key:
        Dotted key, e.g. ``"processed.panel"`` or ``"data.raw"``.
    mkdir:
        Create the directory (for directory-like paths) or the parent directory (for file paths).
    """
    rel = _lookup(load_config("paths"), key)
    if not isinstance(rel, str):
        raise ConfigError(f"'{key}' in config/paths.yaml is a section, not a path")
    if _is_absolute(rel):
        raise ConfigError(f"'{key}' must be relative to the repository root; got {rel!r}")
    path = project_root() / PurePosixPath(rel)
    if mkdir:
        (path if path.suffix == "" else path.parent).mkdir(parents=True, exist_ok=True)
    return path


def iter_path_entries(tree: dict[str, Any] | None = None, prefix: str = "") -> Iterator[tuple[str, str]]:
    """Yield ``(dotted_key, relative_path)`` for every entry in ``config/paths.yaml``."""
    tree = load_config("paths") if tree is None else tree
    for key, value in tree.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            yield from iter_path_entries(value, prefix=f"{dotted}.")
        else:
            yield dotted, value


def require_setting(value: Any, name: str) -> Any:
    """Raise :class:`ConfigError` if an analysis setting is still undecided (``None``)."""
    if value is None or value == []:
        raise ConfigError(
            f"Setting '{name}' is not decided yet (null in config). Set it and log the choice in "
            "docs/decisions.md."
        )
    return value
