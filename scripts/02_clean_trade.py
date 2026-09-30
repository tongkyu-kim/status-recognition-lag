"""Step 02 - clean raw trade data into canonical tables.

Inputs : data/raw/<trade source_id>/<YYYY-MM-DD>/*   (sources with category `trade`)
Outputs: data/interim/trade/bilateral_trade.parquet  (total trade, canonical long schema)
         data/interim/trade/product_trade.parquet    (HS-level rows, if present)

Each source needs `reader` and `column_map` in config/sources.yaml before it can be cleaned.
"""

import _bootstrap  # noqa: F401
import pandas as pd

from srl.acquisition.sources import raw_files, read_raw_source, sources_by_category
from srl.cleaning.trade import standardize_trade_table
from srl.utils.cli import run_step
from srl.utils.config import get_path
from srl.utils.io import MissingInputError, write_table


def main(args, logger) -> None:
    sources = [s for s in sources_by_category("trade") if raw_files(s.source_id)]
    if not sources:
        raise MissingInputError(
            "No raw trade files found. Deposit files under data/raw/<source_id>/<YYYY-MM-DD>/ "
            "for a `trade` source in config/sources.yaml and register them (step 01)."
        )
    tables = []
    for source in sources:
        logger.info("Cleaning %s", source.source_id)
        raw = read_raw_source(source)
        tables.append(standardize_trade_table(raw, source_id=source.source_id,
                                              column_map=source.column_map))
    trade = pd.concat(tables, ignore_index=True)
    totals = trade[trade["product_code"].isna()]
    products = trade[trade["product_code"].notna()]
    write_table(totals, get_path("interim.trade_bilateral"))
    if not products.empty:
        write_table(products, get_path("interim.trade_products"))


if __name__ == "__main__":
    run_step("02_clean_trade", main)
