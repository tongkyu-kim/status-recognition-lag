"""Planned production figures (implemented once real data exist).

Visual design (palette, fonts incl. Korean glyph support, sizes) is decided when the first real
figure is built and recorded in docs/decisions.md; nothing is drawn from placeholder data.
"""

from __future__ import annotations

import pandas as pd


def status_trajectories(panel: pd.DataFrame, status_col: str):
    """Partner status proximity over time (one line per partner, parity reference line)."""
    raise NotImplementedError


def status_vs_recognition(panel: pd.DataFrame, status_col: str, recognition_col: str):
    """Recognition against status proximity with a flexible (e.g., LOWESS/spline) fit (H2)."""
    raise NotImplementedError


def lag_variant_comparison(panel: pd.DataFrame, lag_cols: list[str]):
    """Agreement across recognition-lag operationalizations (rank correlations, trajectories)."""
    raise NotImplementedError


def marginal_effects(result, term: str, moderator: str):
    """Marginal effect of status proximity across a moderator (H3/H4) with uncertainty bands."""
    raise NotImplementedError
