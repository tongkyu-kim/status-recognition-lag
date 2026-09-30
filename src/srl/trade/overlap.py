"""Competitive (structural) overlap between Korea and each partner.

Expected input
--------------
``exports``: product-level exports to the WORLD, long form
``[year, iso3, product, value]``. World-level denominators (RCA) require (close to) all exporting
countries, not only panel members; results depend on the product classification and revision,
which must be fixed and documented.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from srl.utils.validation import check_unique_keys, require_columns

EXPORT_COLUMNS = ["year", "iso3", "product", "value"]


def _validate(exports: pd.DataFrame) -> None:
    require_columns(exports, EXPORT_COLUMNS, "exports")
    check_unique_keys(exports, ["year", "iso3", "product"], "exports")


def export_shares(exports: pd.DataFrame) -> pd.DataFrame:
    """Add ``share`` = :math:`x_{ck} / X_c` (product share in each country's exports, per year)."""
    _validate(exports)
    total = exports.groupby(["year", "iso3"])["value"].transform("sum")
    return exports.assign(share=exports["value"] / total)


def rca(exports: pd.DataFrame) -> pd.DataFrame:
    """Balassa revealed comparative advantage.

    .. math:: RCA_{ck} = \\frac{x_{ck} / X_c}{x_{wk} / X_w}

    with world totals computed over all countries in ``exports``. Returns
    ``[year, iso3, product, rca]``.
    """
    df = export_shares(exports)
    world_k = df.groupby(["year", "product"])["value"].transform("sum")
    world = df.groupby("year")["value"].transform("sum")
    df["rca"] = df["share"] / (world_k / world)
    return df[["year", "iso3", "product", "rca"]]


def export_similarity_index(exports: pd.DataFrame, *, reference: str = "KOR",
                            scale: float = 1.0) -> pd.DataFrame:
    """Finger-Kreinin export similarity with the reference state.

    .. math:: ESI_{jKt} = scale \\times \\sum_k \\min(s_{jkt}, s_{Kkt})

    where :math:`s` are product shares in each country's total exports. 0 = no overlap,
    ``scale`` = identical structure. Returns ``[year, iso3, esi]`` (reference row excluded).
    """
    df = export_shares(exports)
    wide = df.pivot_table(index=["year", "iso3"], columns="product", values="share",
                          aggfunc="sum", fill_value=0.0)
    rows = []
    for year, block in wide.groupby(level="year"):
        block = block.droplevel("year")
        if reference not in block.index:
            continue
        ref = block.loc[reference]
        esi = block.clip(upper=ref, axis=1).sum(axis=1) * scale
        rows.append(pd.DataFrame({"year": year, "iso3": esi.index, "esi": esi.to_numpy()}))
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["year", "iso3", "esi"])
    return out[out["iso3"] != reference].reset_index(drop=True)


def rca_overlap(rca_df: pd.DataFrame, *, reference: str = "KOR", method: str = "jaccard",
                threshold: float = 1.0) -> pd.DataFrame:
    """Overlap in comparative-advantage profiles with the reference state.

    ``method="jaccard"``: share of products in which both have RCA > ``threshold`` among products
    in which either does. ``method="spearman"``: rank correlation of RCA across products.
    Returns ``[year, iso3, rca_overlap]`` (reference row excluded).
    """
    require_columns(rca_df, ["year", "iso3", "product", "rca"], "rca_df")
    wide = rca_df.pivot_table(index=["year", "iso3"], columns="product", values="rca", fill_value=0.0)
    rows = []
    for year, block in wide.groupby(level="year"):
        block = block.droplevel("year")
        if reference not in block.index:
            continue
        ref = block.loc[reference]
        for iso3, row in block.drop(index=reference).iterrows():
            if method == "jaccard":
                a, b = row > threshold, ref > threshold
                union = (a | b).sum()
                value = (a & b).sum() / union if union else np.nan
            elif method == "spearman":
                value = row.rank().corr(ref.rank())
            else:
                raise ValueError("method must be 'jaccard' or 'spearman'")
            rows.append({"year": year, "iso3": iso3, "rca_overlap": float(value)})
    return pd.DataFrame(rows, columns=["year", "iso3", "rca_overlap"])


def composition_similarity(a: pd.Series, b: pd.Series, *, method: str = "cosine") -> float:
    """Similarity of two sector-composition vectors aligned on their index.

    Intended for manufacturing value-added composition by ISIC sector. ``cosine``:
    :math:`a \\cdot b / (\\|a\\| \\|b\\|)`.
    """
    a, b = a.align(b, fill_value=0.0)
    if method != "cosine":
        raise ValueError("only 'cosine' is implemented")
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a.dot(b) / denom) if denom else float("nan")


def sectoral_overlap(*args, **kwargs) -> pd.DataFrame:
    """Overlap in HS-section / ISIC-sector export composition with Korea.

    TODO: requires a fixed HS->sector concordance (stored in data/external/ with provenance) and
    a decision on aggregation level; then reuse :func:`composition_similarity`.
    """
    raise NotImplementedError("Sectoral overlap awaits an HS->sector concordance decision")


def high_value_overlap(*args, **kwargs) -> pd.DataFrame:
    """Overlap restricted to high-value / high-technology products.

    TODO: requires an externally documented product list (e.g., a technology-intensity
    classification of HS codes) chosen ex ante; do not hand-pick products.
    """
    raise NotImplementedError("High-value overlap awaits a documented product classification")
