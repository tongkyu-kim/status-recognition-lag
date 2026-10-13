"""Acquire World Bank historical income classifications (OGHIST) and current classification (CLASS).

Dataset: World Bank Country and Lending Groups, Data Catalog id 0037712
(https://datacatalog.worldbank.org/search/dataset/0037712). Licence: CC BY 4.0.
"""

import argparse

import _bootstrap  # noqa: F401

from srl.acquisition.fetch import PoliteSession, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "wb_income_class"
FILES = {
    "OGHIST.xlsx": "https://datacatalogfiles.worldbank.org/ddh-published/0037712/DR0090754/OGHIST.xlsx",
    "CLASS.xlsx": "https://datacatalogfiles.worldbank.org/ddh-published/0037712/DR0090755/CLASS.xlsx",
}


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=2)
    for name, url in FILES.items():
        resp = sess.get(url)
        resp.raise_for_status()
        save_raw(SOURCE_ID, name, resp.content, url=url, http_status=resp.status_code)
        logger.info("%s: %d bytes", name, len(resp.content))
    write_folder_readme(
        SOURCE_ID,
        f"""
# World Bank income classifications

- `OGHIST.xlsx`: historical classification by income, FY1989-current, with thresholds
  (sheet `Country Analytical History`, thresholds sheet). {FILES["OGHIST.xlsx"]}
- `CLASS.xlsx`: current classification. {FILES["CLASS.xlsx"]}
- Landing page: https://datacatalog.worldbank.org/search/dataset/0037712
- Note: classifications are by World Bank fiscal year (FY). The FY{{t+1}} classification is
  announced on 1 July of calendar year t and is based on GNI per capita (Atlas) of year t-1.
- Licence: CC BY 4.0. Script: scripts/acquire/acq_wb_income.py
""",
    )


if __name__ == "__main__":
    run_step("acq_wb_income", main, argparse.ArgumentParser(description=__doc__))
