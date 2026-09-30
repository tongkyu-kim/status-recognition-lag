"""Macro/indicator cleaning: raw indicator tables -> canonical long schema.

Canonical indicator schema (long):

    iso3       str    ISO3
    year       int
    indicator  str    project-level indicator name (e.g., "gdppc_ppp_const")
    value      float
    unit       str
    source_id  str
"""

from __future__ import annotations

import re

import pandas as pd

from srl.utils.countries import normalize_country_series
from srl.utils.validation import check_iso3, check_unique_keys, require_columns

CANONICAL_INDICATOR_COLUMNS = ["iso3", "year", "indicator", "value", "unit", "source_id"]
INDICATOR_KEYS = ["iso3", "year", "indicator", "source_id"]


def wide_years_to_long(df: pd.DataFrame, id_cols: list[str],
                       year_pattern: str = r"^(\d{4})") -> pd.DataFrame:
    """Reshape a table with one column per year into long form with an integer ``year``.

    Columns whose names do not match ``year_pattern`` and are not in ``id_cols`` are dropped.
    """
    regex = re.compile(year_pattern)
    year_cols = [c for c in df.columns if c not in id_cols and regex.match(str(c))]
    long = df.melt(id_vars=id_cols, value_vars=year_cols, var_name="_year_label", value_name="value")
    long["year"] = long["_year_label"].astype(str).str.extract(regex, expand=False).astype(int)
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    return long.drop(columns="_year_label")


def standardize_indicator_table(raw: pd.DataFrame, *, source_id: str,
                                column_map: dict[str, str] | None,
                                indicator_map: dict[str, str] | None = None) -> pd.DataFrame:
    """Rename, normalize and validate a long-form indicator table.

    ``indicator_map`` maps source indicator codes to project indicator names; unmapped codes
    are dropped so that only deliberately selected indicators enter the pipeline.
    """
    if not column_map:
        raise NotImplementedError(f"No column_map for macro source '{source_id}' in config/sources.yaml")
    df = raw.rename(columns=column_map).copy()
    require_columns(df, ["iso3", "year", "indicator", "value"], source_id)
    if indicator_map:
        df["indicator"] = df["indicator"].map(indicator_map)
        df = df.dropna(subset=["indicator"])
    if "unit" not in df.columns:
        df["unit"] = pd.NA
    df["source_id"] = source_id
    df["iso3"] = normalize_country_series(df["iso3"])
    df = df.dropna(subset=["iso3"])[CANONICAL_INDICATOR_COLUMNS]
    check_iso3(df, "iso3", name=source_id)
    check_unique_keys(df, INDICATOR_KEYS, name=source_id)
    return df


def indicators_to_wide(long: pd.DataFrame, indicators: dict[str, str]) -> pd.DataFrame:
    """Pivot selected indicators to an ``iso3 x year`` table.

    ``indicators`` maps output column names to indicator names, e.g. ``{"gdppc": "gdppc_ppp_const"}``.
    """
    subset = long[long["indicator"].isin(indicators.values())]
    check_unique_keys(subset, ["iso3", "year", "indicator"], name="indicators (one source per indicator)")
    wide = subset.pivot(index=["iso3", "year"], columns="indicator", values="value")
    wide = wide.rename(columns={v: k for k, v in indicators.items()}).reset_index()
    wide.columns.name = None
    return wide
