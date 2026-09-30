"""Step 10 - production figures from the analytical panel and model outputs.

Input : data/processed/panel_partner_year.parquet, outputs/models/*
Output: outputs/figures/<name>.{pdf,png}
Figures are defined in src/srl/figures/plots.py and implemented once real data exist.
"""

import _bootstrap  # noqa: F401

from srl.utils.cli import run_step
from srl.utils.config import get_path
from srl.utils.io import require_inputs


def main(args, logger) -> None:
    require_inputs([get_path("processed.panel")], "Run step 08 first.")
    raise NotImplementedError("Production figures are defined in srl.figures.plots but not built yet")


if __name__ == "__main__":
    run_step("10_make_figures", main)
