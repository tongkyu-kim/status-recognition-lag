"""Uniform harness for pipeline scripts: logging, seeding, and meaningful exit codes.

Exit codes
    0  success
    1  unexpected error (see log)
    2  required input missing (data not yet acquired or upstream step not run)
    3  stage not implemented yet (awaiting data-dependent design decisions)
    4  configuration setting undecided or invalid
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from typing import NoReturn

from srl.utils.config import ConfigError
from srl.utils.io import MissingInputError
from srl.utils.logs import setup_logging
from srl.utils.paths import project_root
from srl.utils.seeds import set_global_seed

EXIT_OK, EXIT_ERROR, EXIT_MISSING_INPUT, EXIT_NOT_IMPLEMENTED, EXIT_CONFIG = 0, 1, 2, 3, 4

StepFn = Callable[[argparse.Namespace, logging.Logger], None]


def run_step(step: str, main: StepFn, parser: argparse.ArgumentParser | None = None) -> NoReturn:
    """Parse arguments, configure logging and seeds, run ``main`` and exit with a status code."""
    parser = parser or argparse.ArgumentParser(description=step)
    parser.add_argument("--log-level", default="INFO", help="Logging level (default: INFO)")
    args = parser.parse_args()

    logger = setup_logging(step, level=args.log_level.upper())
    seed = set_global_seed()
    logger.info("Step %s | seed=%d | root=%s", step, seed, project_root())

    try:
        main(args, logger)
    except MissingInputError as exc:
        logger.error("Missing input: %s", exc)
        sys.exit(EXIT_MISSING_INPUT)
    except NotImplementedError as exc:
        logger.error("Not implemented yet: %s", exc)
        sys.exit(EXIT_NOT_IMPLEMENTED)
    except ConfigError as exc:
        logger.error("Configuration: %s", exc)
        sys.exit(EXIT_CONFIG)
    except Exception:
        logger.exception("Step %s failed", step)
        sys.exit(EXIT_ERROR)

    logger.info("Step %s completed", step)
    sys.exit(EXIT_OK)
