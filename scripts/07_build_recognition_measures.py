"""Step 07 - recognition measures (dictionary baseline) and human-coding samples.

Input : data/interim/text/sentences.parquet, data/interim/text/mentions.parquet
Output: data/interim/text/sentence_frames.parquet
        data/processed/recognition_measures.parquet  [iso3, year, frame counts, recognition_*]
        data/interim/coding_samples/coding_sample_<date>.csv  (with --draw-coding-sample)
"""

import argparse
from datetime import date

import _bootstrap  # noqa: F401

from srl.recognition.aggregation import aggregate_frames, attribute_frames
from srl.recognition.dictionary import load_frame_dictionary, score_sentences
from srl.recognition.index import add_recognition_indices
from srl.recognition.validation import draw_coding_sample
from srl.text.aggregation import add_period
from srl.text.entities import default_matcher
from srl.utils.cli import run_step
from srl.utils.config import get_path, load_config, require_setting
from srl.utils.io import read_table, write_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--draw-coding-sample", action="store_true",
                        help="Also draw a stratified human-coding sample (size from config)")
    parser.add_argument("--mask-countries", action="store_true",
                        help="Mask country names in the coding sample text")
    return parser


def main(args, logger) -> None:
    cfg = load_config("analysis")
    sentences = read_table(get_path("interim.sentences"))
    mentions = read_table(get_path("interim.mentions"))
    ref = load_config("countries")["reference_state"]

    frames_cfg = load_frame_dictionary(cfg["recognition"]["dictionary"])
    logger.info("Frame dictionary version %s (%s)", frames_cfg["version"], frames_cfg["status"])
    scored = score_sentences(sentences, cfg=frames_cfg)
    write_table(scored, get_path("interim.sentence_frames"))

    attributed = attribute_frames(scored, mentions, exclude=(ref,))
    agg = aggregate_frames(attributed, freq="Y")
    agg = add_recognition_indices(agg, methods=tuple(cfg["recognition"]["index_methods"]),
                                  smoothing=cfg["recognition"]["logit_smoothing"])
    out = agg.rename(columns={"entity_id": "iso3"}).assign(year=lambda d: d["period"].astype(int))
    write_table(out.drop(columns="period"), get_path("processed.recognition_measures"))

    if args.draw_coding_sample:
        size = require_setting(cfg["coding_sample"]["size"], "coding_sample.size")
        units = add_period(attributed, freq="Y")
        units["unit_id"] = units["sentence_id"] + "|" + units["entity_id"]
        sample = draw_coding_sample(units, int(size), strata=cfg["coding_sample"]["strata"],
                                    id_col="unit_id")
        if args.mask_countries:
            sample["text"] = sample["text"].map(default_matcher().mask)
        keep = ["coding_order", "unit_id", "sentence_id", "entity_id", "source_id", "date", "text"]
        out_dir = get_path("interim.coding_samples", mkdir=True)
        write_table(sample[keep], out_dir / f"coding_sample_{date.today().isoformat()}.csv")


if __name__ == "__main__":
    run_step("07_build_recognition_measures", main, build_parser())
