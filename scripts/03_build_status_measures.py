"""Step 03 - build objective status, interdependence and competitive-overlap measures.

(a) Clean macro indicator sources  -> data/interim/macro/indicators_long.parquet
(b) Status proximity measures       -> data/processed/status_measures.parquet
(c) Trade-based measures            -> data/processed/trade_measures.parquet

Indicator choices are read from config/analysis.yaml (`status.indicators`); null entries stop
the step with a configuration error rather than silently picking a series.
"""

import _bootstrap  # noqa: F401
import pandas as pd

from srl.acquisition.sources import raw_files, read_raw_source, sources_by_category
from srl.cleaning.macro import indicators_to_wide, standardize_indicator_table
from srl.status.composite import composite_status_proximity
from srl.status.proximity import relative_to_reference
from srl.utils.cli import run_step
from srl.utils.config import get_path, load_config, require_setting
from srl.utils.countries import panel_definition
from srl.utils.io import MissingInputError, read_table, require_inputs, write_table


def clean_macro(logger) -> pd.DataFrame:
    sources = [s for s in sources_by_category("macro") if raw_files(s.source_id)]
    if not sources:
        raise MissingInputError(
            "No raw macro/indicator files found (sources with category `macro` in "
            "config/sources.yaml). Deposit and register them first (step 01)."
        )
    tables = []
    for source in sources:
        logger.info("Cleaning %s", source.source_id)
        tables.append(standardize_indicator_table(read_raw_source(source), source_id=source.source_id,
                                                  column_map=source.column_map))
    long = pd.concat(tables, ignore_index=True)
    write_table(long, get_path("interim.macro_indicators"))
    return long


def build_status(long: pd.DataFrame, cfg: dict, logger) -> pd.DataFrame:
    indicators = {name: code for name, code in cfg["indicators"].items() if code is not None}
    require_setting(indicators or None, "status.indicators (map at least one variable)")
    incumbent, partners = panel_definition(load_config("analysis")["panel"]["name"])
    wide = indicators_to_wide(long, indicators)
    wide = wide[wide["iso3"].isin([incumbent, *partners])].copy()
    for name in indicators:
        wide[f"{name}_prox"] = relative_to_reference(wide, name, reference=incumbent,
                                                     method=cfg["proximity_method"])
    composite = cfg.get("composite") or {}
    if composite.get("components"):
        wide["status_proximity_composite"] = composite_status_proximity(
            wide, composite["components"], method=composite.get("method", "zmean"),
            min_components=composite.get("min_components", 2))
    status = wide[wide["iso3"] != incumbent].reset_index(drop=True)
    logger.info("Status measures: %d partner-years, columns %s", len(status), list(status.columns))
    return status


def main(args, logger) -> None:
    cfg = load_config("analysis")["status"]
    long = clean_macro(logger)
    write_table(build_status(long, cfg, logger), get_path("processed.status_measures"))

    require_inputs([get_path("interim.trade_bilateral")], "Run step 02 first.")
    read_table(get_path("interim.trade_bilateral"))
    raise NotImplementedError(
        "Trade-based measures need Korea's world trade totals and a decision on primary "
        "interdependence/overlap measures (srl.trade.interdependence / srl.trade.overlap). "
        "Wire them here once world totals and HS-level export data are available."
    )


if __name__ == "__main__":
    run_step("03_build_status_measures", main)
