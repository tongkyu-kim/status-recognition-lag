"""Trade cleaning: raw source tables -> canonical trade schemas.

Canonical bilateral/product trade schema (long, one row per flow):

    year               int
    month              int | <NA>     (NA for annual data)
    reporter_iso3      str            (ISO3)
    partner_iso3       str            (ISO3)
    flow               {"export", "import"}
    product_code       str | <NA>     (NA for total trade)
    product_classification str | <NA> (e.g., "HS2017", "HSK")
    value_usd          float          (current USD; deflation decided downstream)
    source_id          str

Korea-perspective bilateral table (from :func:`to_reference_perspective`):

    year, partner_iso3, exports, imports   (Korea's exports to / imports from partner)
"""

from __future__ import annotations

import logging

import pandas as pd

from srl.utils.countries import normalize_country_series, unmatched_names
from srl.utils.validation import check_iso3, check_nonnegative, check_unique_keys, require_columns

logger = logging.getLogger(__name__)

CANONICAL_TRADE_COLUMNS = [
    "year", "month", "reporter_iso3", "partner_iso3", "flow",
    "product_code", "product_classification", "value_usd", "source_id",
]
TRADE_KEYS = ["year", "month", "reporter_iso3", "partner_iso3", "flow", "product_code"]
FLOW_VALUES = {"export", "import"}


def standardize_trade_table(raw: pd.DataFrame, *, source_id: str,
                            column_map: dict[str, str] | None,
                            flow_map: dict[str, str] | None = None) -> pd.DataFrame:
    """Rename, normalize and validate a raw trade table.

    Parameters
    ----------
    raw:
        Raw table as read by :func:`srl.acquisition.sources.read_raw_source`.
    column_map:
        Mapping from raw column names to canonical names (from ``config/sources.yaml``). Reporter
        and partner columns may contain names or ISO3 codes; both are normalized to ISO3.
    flow_map:
        Optional mapping of raw flow labels to ``export``/``import``.
    """
    if not column_map:
        raise NotImplementedError(
            f"No column_map for trade source '{source_id}' in config/sources.yaml"
        )
    df = raw.rename(columns=column_map).copy()
    require_columns(df, ["year", "reporter_iso3", "partner_iso3", "flow", "value_usd"], source_id)
    for col in ("month", "product_code", "product_classification"):
        if col not in df.columns:
            df[col] = pd.NA
    df["source_id"] = source_id

    for col in ("reporter_iso3", "partner_iso3"):
        unmatched = unmatched_names(df[col])
        if unmatched:
            logger.warning("%s: %d unmatched %s values, e.g. %s", source_id, len(unmatched), col,
                           unmatched[:10])
        df[col] = normalize_country_series(df[col])
    if flow_map:
        df["flow"] = df["flow"].map(flow_map)
    bad_flows = set(df["flow"].dropna().unique()) - FLOW_VALUES
    if bad_flows:
        raise ValueError(f"{source_id}: unrecognized flow labels {sorted(bad_flows)}")

    df = df[CANONICAL_TRADE_COLUMNS]
    check_iso3(df, "reporter_iso3", name=source_id)
    check_iso3(df, "partner_iso3", name=source_id)
    check_nonnegative(df, ["value_usd"], name=source_id)
    check_unique_keys(df, TRADE_KEYS, name=source_id)
    return df


def to_reference_perspective(trade: pd.DataFrame, reference: str = "KOR") -> pd.DataFrame:
    """Aggregate canonical total-trade rows to ``[year, partner_iso3, exports, imports]``.

    Uses rows reported by ``reference`` only (reporter-side data). Mirror statistics
    (partner-reported flows) are a separate robustness choice.
    """
    rows = trade[(trade["reporter_iso3"] == reference) & trade["product_code"].isna()]
    wide = (rows.pivot_table(index=["year", "partner_iso3"], columns="flow", values="value_usd",
                             aggfunc="sum")
                .rename(columns={"export": "exports", "import": "imports"})
                .reset_index())
    wide.columns.name = None
    return wide
