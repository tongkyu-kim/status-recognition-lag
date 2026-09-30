"""Logging setup for pipeline steps (console + timestamped file in outputs/diagnostics/logs/)."""

from __future__ import annotations

import logging
from datetime import datetime

from srl.utils.config import get_path

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(step: str, *, level: str | int = "INFO", to_file: bool = True) -> logging.Logger:
    """Configure root logging for a pipeline step and return the step logger."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    formatter = logging.Formatter(_FORMAT, _DATEFMT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if to_file:
        log_dir = get_path("outputs.logs", mkdir=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        file_handler = logging.FileHandler(log_dir / f"{step}_{stamp}.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    return logging.getLogger(step)
