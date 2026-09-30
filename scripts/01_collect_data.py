"""Step 01 - register and verify manually acquired raw files.

This step performs NO downloading or scraping. Raw files are deposited by hand under
``data/raw/<source_id>/<YYYY-MM-DD>/`` (see data/README.md), then:

    python scripts/01_collect_data.py --mode status     # source registry overview
    python scripts/01_collect_data.py --mode register   # checksum new files into the manifest
    python scripts/01_collect_data.py --mode verify     # detect modified/missing/unregistered files
"""

import argparse

import _bootstrap  # noqa: F401

from srl.acquisition.sources import sources_table
from srl.utils import manifest
from srl.utils.cli import run_step


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["status", "register", "verify"], default="verify")
    parser.add_argument("--lock", action="store_true",
                        help="Make newly registered raw files read-only")
    parser.add_argument("--notes", default="", help="Note stored with newly registered files")
    return parser


def main(args, logger) -> None:
    if args.mode == "status":
        table = sources_table()
        logger.info("Configured sources:\n%s", table.to_string(index=False))
        logger.info("Status counts: %s", table["status"].value_counts().to_dict())
        return
    if args.mode == "register":
        new = manifest.register_new_files(notes=args.notes, lock=args.lock)
        for rel in new["relative_path"]:
            logger.info("registered %s", rel)
    report = manifest.verify_manifest()
    problems = report[report["status"] != "ok"]
    for row in problems.itertuples(index=False):
        logger.error("%s: %s", row.status.upper(), row.relative_path)
    if not problems.empty:
        raise manifest.ManifestError(
            f"{len(problems)} raw file problem(s); raw data must not change after registration. "
            "Register new files with --mode register."
        )


if __name__ == "__main__":
    run_step("01_collect_data", main, build_parser())
