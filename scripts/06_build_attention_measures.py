"""Step 06 - government-attention measures per partner-year.

Input : data/interim/text/mentions.parquet
Output: data/processed/attention_measures.parquet  [iso3, year, n_mentions, n_sentences,
        n_documents, *_share]
"""

import _bootstrap  # noqa: F401

from srl.attention.measures import (allocate_group_mentions, attention_share, document_counts,
                                    mention_counts, sentence_counts)
from srl.utils.cli import run_step
from srl.utils.config import get_path, load_config
from srl.utils.io import read_table, write_table


def main(args, logger) -> None:
    cfg = load_config("analysis")["text"]
    if cfg["aggregation_frequency"] != "Y":
        raise NotImplementedError("Only annual aggregation is wired into the partner-year panel")
    mentions = read_table(get_path("interim.mentions"))
    ref = load_config("countries")["reference_state"]

    counts = mention_counts(mentions, entity_types=("country", "group"), exclude=(ref,))
    counts = allocate_group_mentions(counts, "n_mentions", method=cfg["group_mention_allocation"])
    counts = counts.merge(sentence_counts(mentions, exclude=(ref,)), on=["entity_id", "period"],
                          how="left")
    counts = counts.merge(document_counts(mentions, exclude=(ref,)), on=["entity_id", "period"],
                          how="left")
    for col in ("n_mentions", "n_sentences", "n_documents"):
        counts[f"{col}_share"] = attention_share(counts, col)
    out = counts.rename(columns={"entity_id": "iso3"}).assign(year=lambda d: d["period"].astype(int))
    write_table(out.drop(columns="period"), get_path("processed.attention_measures"))


if __name__ == "__main__":
    run_step("06_build_attention_measures", main)
