"""Basic validation checks for intermediate and analytical tables.

Checks raise :class:`ValidationError` with an informative message rather than silently coercing.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd


class ValidationError(ValueError):
    """A table failed a structural or range check."""


def require_columns(df: pd.DataFrame, columns: Iterable[str], name: str = "table") -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValidationError(f"{name}: missing required column(s) {missing}")


def check_unique_keys(df: pd.DataFrame, keys: Sequence[str], name: str = "table") -> None:
    require_columns(df, keys, name)
    dup = df.duplicated(subset=list(keys), keep=False)
    if dup.any():
        example = df.loc[dup, list(keys)].head(5).to_dict("records")
        raise ValidationError(f"{name}: {int(dup.sum())} rows with duplicate keys {keys}, e.g. {example}")


def check_iso3(df: pd.DataFrame, column: str, allowed: Iterable[str] | None = None,
               name: str = "table") -> None:
    require_columns(df, [column], name)
    values = df[column].dropna().astype(str)
    bad_format = values[~values.str.fullmatch(r"[A-Z]{3}")]
    if not bad_format.empty:
        raise ValidationError(f"{name}: non-ISO3 values in '{column}': {sorted(bad_format.unique())[:10]}")
    if allowed is not None:
        unexpected = sorted(set(values) - set(allowed))
        if unexpected:
            raise ValidationError(f"{name}: unexpected codes in '{column}': {unexpected}")


def check_year_range(df: pd.DataFrame, column: str = "year", start: int | None = None,
                     end: int | None = None, name: str = "table") -> None:
    require_columns(df, [column], name)
    years = pd.to_numeric(df[column], errors="raise")
    if start is not None and (years < start).any():
        raise ValidationError(f"{name}: '{column}' has values before {start}")
    if end is not None and (years > end).any():
        raise ValidationError(f"{name}: '{column}' has values after {end}")


def check_nonnegative(df: pd.DataFrame, columns: Iterable[str], name: str = "table") -> None:
    for col in columns:
        require_columns(df, [col], name)
        if (df[col].dropna() < 0).any():
            raise ValidationError(f"{name}: negative values in '{col}'")


def check_bounds(df: pd.DataFrame, columns: Iterable[str], lower: float = 0.0, upper: float = 1.0,
                 name: str = "table") -> None:
    """Check that values lie in [lower, upper] (e.g., shares)."""
    for col in columns:
        require_columns(df, [col], name)
        values = df[col].dropna()
        if ((values < lower) | (values > upper)).any():
            raise ValidationError(f"{name}: '{col}' outside [{lower}, {upper}]")


def missingness_report(df: pd.DataFrame) -> pd.DataFrame:
    """Return per-column counts and shares of missing values."""
    n = len(df)
    missing = df.isna().sum()
    return pd.DataFrame(
        {"column": missing.index, "n_missing": missing.to_numpy(),
         "share_missing": (missing / n).to_numpy() if n else 0.0}
    )
