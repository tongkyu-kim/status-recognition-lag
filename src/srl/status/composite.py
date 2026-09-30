"""Composite status-proximity index combining several proximity components."""

from __future__ import annotations

import numpy as np
import pandas as pd

from srl.utils.validation import require_columns


def _zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd and not np.isnan(sd) else s * np.nan


def composite_status_proximity(df: pd.DataFrame, components: list[str], *, method: str = "zmean",
                               weights: dict[str, float] | None = None,
                               min_components: int = 2) -> pd.Series:
    """Combine proximity components into one index.

    ``method="zmean"``: (weighted) mean of pooled z-scores of the components, computed where at
    least ``min_components`` are observed. Pooled standardization keeps over-time change visible;
    within-year standardization would remove common trends (a different concept).

    ``method="pca"``: first principal component (not yet implemented; requires decisions on
    missing-data handling and sign normalization).
    """
    require_columns(df, components, "composite input")
    if method == "pca":
        raise NotImplementedError("PCA composite awaits missing-data and sign conventions")
    if method != "zmean":
        raise ValueError("method must be 'zmean' or 'pca'")
    z = pd.DataFrame({c: _zscore(df[c].astype(float)) for c in components})
    w = pd.Series({c: (weights or {}).get(c, 1.0) for c in components})
    observed = z.notna()
    weighted_sum = (z.fillna(0.0) * w).sum(axis=1)
    weight_total = (observed * w).sum(axis=1)
    index = weighted_sum / weight_total
    index[observed.sum(axis=1) < min_components] = np.nan
    return index.rename("status_proximity_composite")
