"""Export sophistication (Hausmann, Hwang & Rodrik 2007: PRODY / EXPY).

.. math::

    PRODY_{kt} = \\sum_c \\frac{x_{ckt}/X_{ct}}{\\sum_{c'} x_{c'kt}/X_{c't}} \\; Y_{ct}

    EXPY_{ct} = \\sum_k \\frac{x_{ckt}}{X_{ct}} PRODY_{kt}

where :math:`Y_{ct}` is GDP per capita. PRODY requires a broad (near-global) country sample; the
choice of classification level, country sample and whether PRODY is time-varying or fixed must be
documented.
"""

from __future__ import annotations

import pandas as pd

from srl.utils.validation import check_unique_keys, require_columns


def prody(exports: pd.DataFrame, gdppc: pd.DataFrame) -> pd.DataFrame:
    """Compute ``[year, product, prody]`` from exports ``[year, iso3, product, value]`` and
    ``gdppc`` ``[iso3, year, gdppc]``. Countries without GDPpc are excluded from the weights."""
    require_columns(exports, ["year", "iso3", "product", "value"], "exports")
    require_columns(gdppc, ["iso3", "year", "gdppc"], "gdppc")
    check_unique_keys(gdppc, ["iso3", "year"], "gdppc")
    df = exports.merge(gdppc, on=["iso3", "year"], how="inner")
    df["share"] = df["value"] / df.groupby(["year", "iso3"])["value"].transform("sum")
    df["weight"] = df["share"] / df.groupby(["year", "product"])["share"].transform("sum")
    df["contrib"] = df["weight"] * df["gdppc"]
    return df.groupby(["year", "product"], as_index=False)["contrib"].sum().rename(
        columns={"contrib": "prody"})


def expy(exports: pd.DataFrame, prody_df: pd.DataFrame) -> pd.DataFrame:
    """Compute ``[year, iso3, expy]`` as the export-share-weighted mean of PRODY."""
    df = exports.merge(prody_df, on=["year", "product"], how="inner")
    df["share"] = df["value"] / df.groupby(["year", "iso3"])["value"].transform("sum")
    df["contrib"] = df["share"] * df["prody"]
    return df.groupby(["year", "iso3"], as_index=False)["contrib"].sum().rename(
        columns={"contrib": "expy"})
