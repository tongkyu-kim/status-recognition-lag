"""Economic interdependence measures (Korea's exposure to each partner).

Expected inputs
---------------
``bilateral``: Korea-perspective table ``[year, partner_iso3, exports, imports]`` (current USD),
    from :func:`srl.cleaning.trade.to_reference_perspective`.
``totals``: Korea's total trade with the world ``[year, total_exports, total_imports]``. This must
    come from world totals, NOT from summing panel partners (the panel omits most partners).

All functions return a DataFrame keyed by ``[year, partner_iso3]`` (or the documented keys) with
the new measure column, leaving inputs unchanged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from srl.utils.validation import check_unique_keys, require_columns

KEYS = ["year", "partner_iso3"]


def _merge_totals(bilateral: pd.DataFrame, totals: pd.DataFrame) -> pd.DataFrame:
    require_columns(bilateral, [*KEYS, "exports", "imports"], "bilateral")
    require_columns(totals, ["year", "total_exports", "total_imports"], "totals")
    check_unique_keys(bilateral, KEYS, "bilateral")
    check_unique_keys(totals, ["year"], "totals")
    return bilateral.merge(totals, on="year", how="left", validate="many_to_one")


def bilateral_trade_share(bilateral: pd.DataFrame, totals: pd.DataFrame) -> pd.DataFrame:
    """Partner's share in Korea's total trade.

    .. math:: TS_{jt} = (X_{Kjt} + M_{Kjt}) / (X_{Kt} + M_{Kt})

    where :math:`X_{Kjt}` / :math:`M_{Kjt}` are Korea's exports to / imports from partner *j*.
    """
    df = _merge_totals(bilateral, totals)
    df["trade_share"] = (df["exports"] + df["imports"]) / (df["total_exports"] + df["total_imports"])
    return df[[*KEYS, "trade_share"]]


def export_dependence(bilateral: pd.DataFrame, totals: pd.DataFrame) -> pd.DataFrame:
    """Share of Korea's exports going to the partner: :math:`X_{Kjt} / X_{Kt}`.

    Alternative (not implemented until GDP data exist): normalize by Korean GDP,
    :math:`X_{Kjt} / GDP_{Kt}`, which captures exposure of the economy rather than of trade.
    """
    df = _merge_totals(bilateral, totals)
    df["export_dependence"] = df["exports"] / df["total_exports"]
    return df[[*KEYS, "export_dependence"]]


def import_dependence(bilateral: pd.DataFrame, totals: pd.DataFrame) -> pd.DataFrame:
    """Share of Korea's imports sourced from the partner: :math:`M_{Kjt} / M_{Kt}`."""
    df = _merge_totals(bilateral, totals)
    df["import_dependence"] = df["imports"] / df["total_imports"]
    return df[[*KEYS, "import_dependence"]]


def trade_growth(df: pd.DataFrame, value_col: str, *, entity_col: str = "partner_iso3",
                 time_col: str = "year", periods: int = 1, method: str = "log") -> pd.Series:
    """Growth of ``value_col`` within entity over ``periods`` time steps.

    ``method="log"``: :math:`\\ln v_t - \\ln v_{t-k}`; ``method="pct"``: :math:`v_t / v_{t-k} - 1`.
    Assumes a complete, gap-free time index per entity (lags are positional).
    """
    ordered = df.sort_values([entity_col, time_col])
    lagged = ordered.groupby(entity_col)[value_col].shift(periods)
    if method == "log":
        with np.errstate(divide="ignore", invalid="ignore"):
            growth = np.log(ordered[value_col]) - np.log(lagged)
    elif method == "pct":
        growth = ordered[value_col] / lagged - 1
    else:
        raise ValueError("method must be 'log' or 'pct'")
    return growth.replace([np.inf, -np.inf], np.nan).reindex(df.index)


def rolling_trade_exposure(df: pd.DataFrame, value_col: str, *, window: int = 3,
                           entity_col: str = "partner_iso3", time_col: str = "year",
                           min_periods: int | None = None) -> pd.Series:
    """Trailing rolling mean of an exposure measure (e.g., trade share) within entity.

    Smooths year-to-year noise; ``window`` and ``min_periods`` are analysis choices to log.
    """
    ordered = df.sort_values([entity_col, time_col])
    rolled = (ordered.groupby(entity_col)[value_col]
                     .transform(lambda s: s.rolling(window, min_periods=min_periods or window).mean()))
    return rolled.reindex(df.index)


def hhi(values: pd.Series | np.ndarray, *, normalize: bool = True) -> float:
    """Herfindahl-Hirschman index :math:`\\sum_k s_k^2` (on the 0-1 scale).

    If ``normalize``, raw values are converted to shares first.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0 or arr.sum() == 0:
        return float("nan")
    shares = arr / arr.sum() if normalize else arr
    return float(np.sum(shares**2))


def trade_concentration(df: pd.DataFrame, value_col: str, group_cols: list[str]) -> pd.DataFrame:
    """HHI of ``value_col`` across rows within each group.

    Examples: product concentration of Korea's imports from partner *j*
    (``group_cols=["year", "partner_iso3"]`` over HS-product rows), or supplier concentration of
    Korea's imports of product *k* (``group_cols=["year", "product_code"]`` over partner rows).
    """
    out = df.groupby(group_cols)[value_col].apply(hhi).rename("hhi").reset_index()
    return out


def fdi_exposure(*args, **kwargs) -> pd.DataFrame:
    """Korean FDI stock/flows to the partner relative to Korea's total outward FDI.

    TODO: implement once a validated bilateral FDI source is chosen (flows vs. stocks,
    approval vs. arrival basis, negative flows, confidentiality suppression).
    """
    raise NotImplementedError("FDI exposure awaits a validated bilateral FDI source")


def gvc_exposure(*args, **kwargs) -> pd.DataFrame:
    """Korea's global-value-chain exposure to the partner (e.g., foreign value added content).

    TODO: implement once an input-output source (country coverage incl. ASEAN members) is chosen.
    """
    raise NotImplementedError("GVC exposure awaits a validated input-output source")
