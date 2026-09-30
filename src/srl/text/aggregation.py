"""Temporal aggregation helpers shared by attention and recognition measures."""

from __future__ import annotations

import pandas as pd

FREQUENCIES = {"Y", "Q", "M"}


def add_period(df: pd.DataFrame, *, date_col: str = "date", freq: str = "Y") -> pd.DataFrame:
    """Return a copy with ``period`` (string label, e.g. ``2019``, ``2019Q3``, ``2019-07``) and
    integer ``year`` derived from ``date_col``."""
    if freq not in FREQUENCIES:
        raise ValueError(f"freq must be one of {sorted(FREQUENCIES)}")
    dates = pd.to_datetime(df[date_col], errors="raise")
    return df.assign(year=dates.dt.year.astype(int), period=dates.dt.to_period(freq).astype(str))


def aggregate(df: pd.DataFrame, value_cols: list[str], *, by: list[str], freq: str = "Y",
              date_col: str = "date", how: str = "sum") -> pd.DataFrame:
    """Aggregate ``value_cols`` by ``by`` + period."""
    with_period = add_period(df, date_col=date_col, freq=freq)
    return with_period.groupby([*by, "period"], as_index=False)[value_cols].agg(how)
