"""Human validation: coding-sample draws and inter-coder reliability."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from srl.utils.seeds import get_seed


def draw_coding_sample(units: pd.DataFrame, n: int, *, strata: list[str] | None = None,
                       seed: int | None = None, id_col: str = "sentence_id") -> pd.DataFrame:
    """Draw a reproducible coding sample.

    With ``strata``, allocates ``ceil(n / n_strata)`` units per stratum (fewer if a stratum is
    smaller), which over-represents rare strata relative to proportional allocation; record
    sampling weights if population estimates are needed. Output order is shuffled (coders
    should not see units grouped by country or year) and numbered in ``coding_order``.
    """
    seed = get_seed() if seed is None else seed
    if strata:
        groups = [g for _, g in units.groupby(strata, sort=True, dropna=False)]
        per = math.ceil(n / max(len(groups), 1))
        sample = pd.concat([g.sample(n=min(per, len(g)), random_state=seed) for g in groups])
    else:
        sample = units.sample(n=min(n, len(units)), random_state=seed)
    if sample[id_col].duplicated().any():
        raise ValueError(f"Duplicate {id_col} in coding sample")
    sample = sample.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return sample.assign(coding_order=np.arange(1, len(sample) + 1))


def percent_agreement(a, b) -> float:
    a, b = pd.Series(list(a)), pd.Series(list(b))
    mask = a.notna() & b.notna()
    return float((a[mask] == b[mask]).mean()) if mask.any() else float("nan")


def cohen_kappa(a, b) -> float:
    """Cohen's kappa for two coders over the same units (nominal categories)."""
    a, b = pd.Series(list(a)), pd.Series(list(b))
    mask = a.notna() & b.notna()
    a, b = a[mask].to_numpy(), b[mask].to_numpy()
    if len(a) == 0:
        return float("nan")
    categories = np.union1d(a, b)
    po = float(np.mean(a == b))
    pe = float(sum(np.mean(a == c) * np.mean(b == c) for c in categories))
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def krippendorff_alpha_nominal(data: pd.DataFrame | np.ndarray) -> float:
    """Krippendorff's alpha for nominal data.

    ``data``: units x coders (rows = units, columns = coders), NaN for missing codes. Units with
    fewer than two codes are ignored. Returns NaN when there is no variation in the data.

    .. math:: \\alpha = 1 - (n - 1) \\frac{\\sum_{c \\ne k} o_{ck}}{\\sum_{c \\ne k} n_c n_k}
    """
    frame = pd.DataFrame(data)
    values = [v for v in frame.to_numpy().ravel() if pd.notna(v)]
    categories = sorted(set(values), key=str)
    index = {c: i for i, c in enumerate(categories)}
    o = np.zeros((len(categories), len(categories)))
    for row in frame.itertuples(index=False):
        codes = [v for v in row if pd.notna(v)]
        m = len(codes)
        if m < 2:
            continue
        for i, ci in enumerate(codes):
            for j, cj in enumerate(codes):
                if i != j:
                    o[index[ci], index[cj]] += 1.0 / (m - 1)
    n_c = o.sum(axis=1)
    n = n_c.sum()
    observed = o.sum() - np.trace(o)
    expected = n_c.sum() ** 2 - (n_c**2).sum()
    if n <= 1 or expected == 0:
        return float("nan")
    return float(1.0 - (n - 1) * observed / expected)
