"""Recognition-lag operationalizations (computed side by side, never hard-coded).

Conceptual target::

    RecognitionLag = ExpectedRecognition(ObjectiveStatus) - ObservedRecognition

SIGN CONVENTION (all variants): positive values = observed recognition BELOW the level implied by
objective status (under-recognition); negative = over-recognition.

Approach A  standardized difference   z(status) - z(recognition)
Approach B  residual recognition      fitted E[recognition | status, ...] - observed recognition
Approach C  dynamic adjustment        speed at which recognition responds to status changes

See docs/research_design.md for advantages and risks. Important: using a lag measure that is
constructed from status as an outcome in a regression on status induces mechanical correlation;
the main models therefore use observed recognition as outcome (config/models.yaml).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm

from srl.utils.config import require_setting
from srl.utils.validation import require_columns

SIGN_CONVENTION = "positive = observed recognition below status-implied expectation"


def _zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd and not np.isnan(sd) else s * np.nan


def _standardize(df: pd.DataFrame, col: str, scope: str, entity_col: str, time_col: str) -> pd.Series:
    values = df[col].astype(float)
    if scope == "pooled":
        return _zscore(values)
    if scope == "within_year":
        return values.groupby(df[time_col]).transform(_zscore)
    if scope == "within_entity":
        return values.groupby(df[entity_col]).transform(_zscore)
    raise ValueError("scope must be 'pooled', 'within_year' or 'within_entity'")


def lag_standardized_difference(df: pd.DataFrame, status_col: str, recognition_col: str, *,
                                scope: str = "pooled", entity_col: str = "iso3",
                                time_col: str = "year") -> pd.Series:
    """Approach A: ``z(status) - z(recognition)``.

    ``scope`` sets the standardization reference: ``pooled`` (all partner-years), ``within_year``
    (relative position among partners in a year; removes common trends) or ``within_entity``
    (over-time deviations within a partner). Assumes both measures are comparable once
    standardized - a strong assumption, since their scales and distributions differ.
    """
    require_columns(df, [status_col, recognition_col, entity_col, time_col], "lag input")
    z_s = _standardize(df, status_col, scope, entity_col, time_col)
    z_r = _standardize(df, recognition_col, scope, entity_col, time_col)
    return (z_s - z_r).rename(f"lag_A_{scope}")


def lag_residual(df: pd.DataFrame, status_col: str | Sequence[str], recognition_col: str, *,
                 functional_form: str = "linear", controls: Sequence[str] = (),
                 time_effects: bool = False, entity_col: str = "iso3",
                 time_col: str = "year") -> pd.Series:
    """Approach B: expected recognition from OLS on status; lag = fitted - observed.

    ``functional_form``: ``linear`` or ``quadratic`` in each status variable. ``time_effects``
    adds year dummies (expectation relative to the same year). Entity fixed effects are
    deliberately not offered: they would absorb persistent under-recognition, which is part of
    the quantity of interest.
    """
    status_cols = [status_col] if isinstance(status_col, str) else list(status_col)
    require_columns(df, [*status_cols, recognition_col, *controls, time_col], "lag input")
    X = df[status_cols].astype(float)
    if functional_form == "quadratic":
        for col in status_cols:
            X[f"{col}_sq"] = X[col] ** 2
    elif functional_form != "linear":
        raise ValueError("functional_form must be 'linear' or 'quadratic'")
    if controls:
        X = X.join(df[list(controls)].astype(float))
    if time_effects:
        X = X.join(pd.get_dummies(df[time_col], prefix="t", drop_first=True, dtype=float))
    X = sm.add_constant(X, has_constant="add")
    y = df[recognition_col].astype(float)
    mask = X.notna().all(axis=1) & y.notna()
    if mask.sum() <= X.shape[1]:
        raise ValueError("Too few complete observations to estimate expected recognition")
    fit = sm.OLS(y[mask], X[mask]).fit()
    lag = pd.Series(np.nan, index=df.index, name=f"lag_B_{functional_form}")
    lag.loc[mask] = fit.fittedvalues - y[mask]
    return lag


def dynamic_adjustment(df: pd.DataFrame, status_col: str, recognition_col: str, **kwargs) -> Any:
    """Approach C: does recognition adjust more slowly than status?

    Candidate designs (to be fixed before estimation):

    - partial adjustment / error-correction: estimate a long-run relation
      ``R* = a + b S`` and the adjustment speed ``lambda`` in
      ``dR_t = lambda (R*_{t-1} - R_{t-1}) + g dS_t + e_t``; lag = slow adjustment (small lambda);
    - local projections of recognition on status changes at horizons h = 0..H;
    - comparison of distributed-lag profiles of recognition vs. attention on status.

    Requires sufficiently long, frequent series per partner; feasibility depends on the corpus.
    """
    raise NotImplementedError("Approach C (dynamic adjustment) design not fixed yet")


LAG_METHODS: dict[str, Callable[..., Any]] = {
    "A_standardized_difference": lag_standardized_difference,
    "B_residual": lag_residual,
    "C_dynamic_adjustment": dynamic_adjustment,
}


def compute_lag_variants(df: pd.DataFrame, variants: Sequence[dict[str, Any]]) -> pd.DataFrame:
    """Compute every configured variant (``config/analysis.yaml`` -> ``recognition_lag.variants``).

    Returns a DataFrame aligned with ``df`` with one column per variant ``name``.
    """
    out = {}
    for variant in variants:
        name = variant["name"]
        method = LAG_METHODS[variant["method"]]
        status_col = require_setting(variant.get("status_col"), f"recognition_lag.{name}.status_col")
        recog_col = require_setting(variant.get("recognition_col"),
                                    f"recognition_lag.{name}.recognition_col")
        out[name] = method(df, status_col, recog_col, **(variant.get("kwargs") or {}))
    return pd.DataFrame(out, index=df.index)
