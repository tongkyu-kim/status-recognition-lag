"""Make ``srl`` importable when scripts run without ``pip install -e .``."""

import sys
from pathlib import Path

try:
    import srl  # noqa: F401
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
