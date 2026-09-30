"""Step 05 - segment documents into sentences and extract country/group mentions.

Input : data/interim/text/documents.parquet
Output: data/interim/text/sentences.parquet, data/interim/text/mentions.parquet
        outputs/diagnostics/mention_surface_counts.csv  (for KWIC / alias validation)
"""

import _bootstrap  # noqa: F401

from srl.text.corpus import build_sentence_and_mention_tables
from srl.text.entities import EntityMatcher
from srl.utils.cli import run_step
from srl.utils.config import get_path, load_config
from srl.utils.io import read_table, write_table


def main(args, logger) -> None:
    cfg = load_config("analysis")["text"]
    docs = read_table(get_path("interim.documents"))
    matcher = EntityMatcher(include_demonyms=cfg["include_demonyms"])
    sentences, mentions = build_sentence_and_mention_tables(
        docs, matcher, min_chars=cfg["min_sentence_chars"])
    logger.info("%d sentences, %d mentions", len(sentences), len(mentions))
    write_table(sentences, get_path("interim.sentences"))
    write_table(mentions, get_path("interim.mentions"))
    surfaces = (mentions.groupby(["entity_id", "surface"]).size().rename("n").reset_index()
                        .sort_values(["entity_id", "n"], ascending=[True, False]))
    write_table(surfaces, get_path("outputs.diagnostics", mkdir=True) / "mention_surface_counts.csv")


if __name__ == "__main__":
    run_step("05_process_text", main)
