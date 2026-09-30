"""Step 04 - assemble the government-text document table from deposited raw files.

No scraping. Documents are deposited under data/raw/<source_id>/<YYYY-MM-DD>/ together with a
`metadata.csv` sidecar (schema in src/srl/text/metadata.py and data/README.md), registered via
step 01, and assembled here into data/interim/text/documents.parquet.
"""

import _bootstrap  # noqa: F401

from srl.text.corpus import build_document_table
from srl.utils import manifest
from srl.utils.cli import run_step
from srl.utils.config import get_path
from srl.utils.io import MissingInputError, write_table


def main(args, logger) -> None:
    report = manifest.verify_manifest()
    if (report["status"] != "ok").any():
        logger.warning("Raw manifest has problems; run step 01 (--mode verify) for details")
    docs = build_document_table()
    if docs.empty:
        raise MissingInputError(
            "No government-text documents found: deposit files plus metadata.csv under "
            "data/raw/<source_id>/<YYYY-MM-DD>/ for a `government_text` source."
        )
    logger.info("Documents by source:\n%s", docs.groupby(["source_id", "language"]).size().to_string())
    write_table(docs, get_path("interim.documents"))


if __name__ == "__main__":
    run_step("04_collect_government_text", main)
