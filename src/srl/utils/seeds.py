"""Deterministic seeding. The project seed is ``seed`` in ``config/analysis.yaml``."""

from __future__ import annotations

import random

import numpy as np

from srl.utils.config import load_config


def get_seed() -> int:
    return int(load_config("analysis")["seed"])


def set_global_seed(seed: int | None = None) -> int:
    """Seed Python's and NumPy's global RNGs and return the seed used.

    Prefer passing an explicit ``numpy.random.Generator`` (``make_rng``) or ``random_state`` to
    functions that sample; global seeding is a backstop for third-party code.
    """
    seed = get_seed() if seed is None else int(seed)
    random.seed(seed)
    np.random.seed(seed % (2**32))
    return seed


def make_rng(seed: int | None = None) -> np.random.Generator:
    return np.random.default_rng(get_seed() if seed is None else seed)
