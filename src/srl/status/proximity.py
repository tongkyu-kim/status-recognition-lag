"""Status proximity: each partner's position on a material dimension relative to Korea.

Expected input: ``iso3 x year`` table containing the incumbent's rows and the indicator column.

Caution: "lower-ranked state approaching the incumbent" does not hold on every dimension for
every partner (e.g., Singapore exceeds Korea in GDP per capita; China exceeds Korea in aggregate
size). Methods therefore keep the sign/direction explicit, and dimension choice is a design
decision (docs/research_design.md).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from srl.utils.validation import ValidationError, require_columns

logger = logging.getLogger(__name__)

METHODS = ("ratio", "log_ratio", "gap", "abs_log_gap")


def relative_to_reference(df: pd.DataFrame, value_col: str, *, reference: str = "KOR",
                          method: str = "log_ratio", entity_col: str = "iso3",
                          time_col: str = "year") -> pd.Series:
    """Partner value relative to the reference state in the same period.

    Methods (x = partner, r = reference):

    - ``ratio``:       x / r      (1 = parity; <1 below Korea)
    - ``log_ratio``:   ln(x / r)  (0 = parity; negative below Korea; symmetric in proportional gaps)
    - ``gap``:         x - r      (level difference; unit-dependent)
    - ``abs_log_gap``: -|ln(x / r)|  (closeness irrespective of side; 0 = parity)

    Returns a Series aligned with ``df``; reference rows get parity values.
    """
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    require_columns(df, [entity_col, time_col, value_col], "status input")
    ref = df.loc[df[entity_col] == reference, [time_col, value_col]]
    if ref[time_col].duplicated().any():
        raise ValidationError(f"Duplicate reference rows for {reference}")
    ref_values = df[time_col].map(ref.set_index(time_col)[value_col])
    if ref_values.isna().all():
        logger.warning("No reference (%s) values for %s", reference, value_col)

    x = df[value_col].astype(float)
    r = ref_values.astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        if method == "ratio":
            out = x / r
        elif method == "log_ratio":
            out = np.log(x / r)
        elif method == "gap":
            out = x - r
        else:
            out = -np.abs(np.log(x / r))
    out = pd.Series(out, index=df.index).replace([np.inf, -np.inf], np.nan)
    return out.rename(f"{value_col}_prox")


def gdppc_proximity(df: pd.DataFrame, value_col: str = "gdppc", **kwargs) -> pd.Series:
    """GDP per capita proximity. Use constant-price PPP GDPpc for cross-country level comparisons;
    record the chosen series in docs/variable_dictionary.md."""
    return relative_to_reference(df, value_col, **kwargs)


def productivity_proximity(df: pd.DataFrame, value_col: str = "productivity", **kwargs) -> pd.Series:
    """Labour-productivity proximity (output per worker or per hour; definition TBD by source)."""
    return relative_to_reference(df, value_col, **kwargs)


def mva_proximity(df: pd.DataFrame, value_col: str = "mva", **kwargs) -> pd.Series:
    """Manufacturing value added proximity. Decide between per-capita MVA (capability) and MVA
    share of GDP (structure) - they capture different concepts."""
    return relative_to_reference(df, value_col, **kwargs)


def hightech_export_proximity(df: pd.DataFrame, value_col: str = "hightech_export_share",
                              **kwargs) -> pd.Series:
    """High-technology export share proximity. Note: shares are sensitive to processing trade
    (assembly-based high-tech exports may overstate domestic capability)."""
    return relative_to_reference(df, value_col, **kwargs)


def patent_proximity(*args, **kwargs) -> pd.Series:
    """Technological-capability proximity from patent data.

    TODO: decide counting rules (office, families vs. applications, fractional counting,
    per-capita normalization) before implementing.
    """
    raise NotImplementedError("Patent proximity awaits counting-rule decisions")
