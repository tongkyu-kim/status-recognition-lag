"""Step 08 - assemble the partner-year analytical panel.

Inputs : data/processed/{status,trade,attention,recognition}_measures.parquet
Output : data/processed/panel_partner_year.parquet
         outputs/diagnostics/panel_missingness.csv
Recognition-lag variants from config/analysis.yaml are added side by side.
"""

import _bootstrap  # noqa: F401

from srl.panel.build import merge_components, panel_skeleton
from srl.recognition.lag import compute_lag_variants
from srl.utils.cli import run_step
from srl.utils.config import get_path, load_config
from srl.utils.io import read_table, require_inputs, write_table
from srl.utils.validation import check_unique_keys, missingness_report

COMPONENTS = {
    "status": "processed.status_measures",
    "trade": "processed.trade_measures",
    "attention": "processed.attention_measures",
    "recognition": "processed.recognition_measures",
}


def main(args, logger) -> None:
    paths = {name: get_path(key) for name, key in COMPONENTS.items()}
    require_inputs(paths.values(), "Run steps 03, 06 and 07 first.")
    skeleton = panel_skeleton()
    components = {name: read_table(path) for name, path in paths.items()}
    panel = merge_components(skeleton, components)
    check_unique_keys(panel, ["iso3", "year"], "panel")

    variants = load_config("analysis")["recognition_lag"]["variants"]
    lags = compute_lag_variants(panel, variants)
    panel = panel.join(lags)

    write_table(panel, get_path("processed.panel"))
    write_table(missingness_report(panel),
                get_path("outputs.diagnostics", mkdir=True) / "panel_missingness.csv")


if __name__ == "__main__":
    run_step("08_build_panel", main)
