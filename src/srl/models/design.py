"""Design-matrix construction: distributed lags, polynomial terms and interactions."""

from __future__ import annotations

import pandas as pd

from srl.models.specs import ModelSpec
from srl.utils.validation import require_columns


def build_design(panel: pd.DataFrame, spec: ModelSpec, *, entity_col: str = "iso3",
                 time_col: str = "year") -> tuple[pd.DataFrame, list[str]]:
    """Return ``(data, exog_columns)`` for ``spec``.

    - lags: ``{var: (0, 1, 2)}`` -> ``var``, ``var_l1``, ``var_l2`` (positional, within entity);
      variables without a lag entry enter contemporaneously.
    - polynomial: ``{var: 2}`` -> adds ``var_p2`` (uses the contemporaneous term).
    - interactions: ``(a, b)`` -> ``a_x_b``; mean-centred components if ``center_interactions``
      (main effects stay uncentred; centring only changes their interpretation, not the fit).
    """
    base_vars = [spec.outcome, *spec.regressors, *spec.controls,
                 *(v for pair in spec.interactions for v in pair)]
    require_columns(panel, [entity_col, time_col, *base_vars], f"panel for {spec.name}")
    df = panel.sort_values([entity_col, time_col]).copy()
    exog: list[str] = []

    for var in [*spec.regressors, *spec.controls]:
        for k in spec.lags.get(var, (0,)):
            col = var if k == 0 else f"{var}_l{k}"
            if k > 0:
                df[col] = df.groupby(entity_col)[var].shift(k)
            exog.append(col)

    for var, degree in spec.polynomial.items():
        for d in range(2, int(degree) + 1):
            col = f"{var}_p{d}"
            df[col] = df[var] ** d
            exog.append(col)

    for a, b in spec.interactions:
        va, vb = df[a].astype(float), df[b].astype(float)
        if spec.center_interactions:
            va, vb = va - va.mean(), vb - vb.mean()
        col = f"{a}_x_{b}"
        df[col] = va * vb
        exog.append(col)

    return df, list(dict.fromkeys(exog))
