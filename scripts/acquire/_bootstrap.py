"""Make ``srl`` importable when acquisition scripts run without ``pip install -e .``."""

import sys
from pathlib import Path

try:
    import srl  # noqa: F401
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
