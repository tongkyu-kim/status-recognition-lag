"""Build the partner-year panel from component tables.

Unit: directed dyad Korea -> partner, annual (``iso3`` = partner, ``year``). Every component is
merged onto a complete skeleton of partners x years so that lags are positional and missingness is
explicit rather than hidden by absent rows.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

import pandas as pd

from srl.utils.config import load_config, require_setting
from srl.utils.countries import panel_definition
from srl.utils.validation import check_unique_keys, require_columns

logger = logging.getLogger(__name__)

PANEL_KEYS = ["iso3", "year"]


def panel_skeleton(panel: str | None = None, start_year: int | None = None,
                   end_year: int | None = None) -> pd.DataFrame:
    """Complete grid of partners x years (defaults from ``config/analysis.yaml``)."""
    cfg = load_config("analysis")["panel"]
    panel = panel or cfg["name"]
    start = require_setting(start_year if start_year is not None else cfg.get("start_year"),
                            "panel.start_year")
    end = require_setting(end_year if end_year is not None else cfg.get("end_year"), "panel.end_year")
    _, partners = panel_definition(panel)
    idx = pd.MultiIndex.from_product([partners, range(int(start), int(end) + 1)], names=PANEL_KEYS)
    return idx.to_frame(index=False)


def merge_components(skeleton: pd.DataFrame, components: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Left-merge component tables keyed by ``[iso3, year]`` onto the skeleton.

    Raises if a component has duplicate keys or reuses a column name already in the panel; logs
    the share of skeleton rows covered by each component.
    """
    panel = skeleton.copy()
    for name, comp in components.items():
        require_columns(comp, PANEL_KEYS, name)
        check_unique_keys(comp, PANEL_KEYS, name)
        clash = (set(comp.columns) - set(PANEL_KEYS)) & set(panel.columns)
        if clash:
            raise ValueError(f"Component '{name}' reuses existing column(s): {sorted(clash)}")
        outside = comp.merge(skeleton, on=PANEL_KEYS, how="left", indicator=True)
        n_outside = int((outside["_merge"] == "left_only").sum())
        if n_outside:
            logger.info("%s: %d rows outside the panel skeleton dropped", name, n_outside)
        panel = panel.merge(comp, on=PANEL_KEYS, how="left", validate="one_to_one")
        covered = panel[[c for c in comp.columns if c not in PANEL_KEYS]].notna().any(axis=1).mean()
        logger.info("%s: covers %.1f%% of partner-years", name, 100 * covered)
    return panel


def add_lags(df: pd.DataFrame, columns: list[str], lags: list[int], *, entity_col: str = "iso3",
             time_col: str = "year") -> pd.DataFrame:
    """Add ``<col>_l<k>`` columns (positional within entity; assumes a complete grid)."""
    out = df.sort_values([entity_col, time_col]).copy()
    for col in columns:
        for k in lags:
            out[f"{col}_l{k}"] = out.groupby(entity_col)[col].shift(k)
    return out
