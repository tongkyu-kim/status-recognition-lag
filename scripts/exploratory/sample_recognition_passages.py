# -*- coding: utf-8 -*-
"""Build a stratified, economic/industrial-relevance-filtered sample of Korea->China passages for
R0-R5 recognition classification (docs/measurement_protocol.md).

Reuses the legacy pilot's sentence-level extraction (data/interim/pilot/partner_sentences.parquet,
built by scripts/pilot/build_frames.py) -- no new acquisition needed; entity matching and sentence
segmentation are language-mechanical steps independent of the H/V/C dictionary this project does
not reuse as the primary measure.

Relevance filter: a Korean keyword list for economic/industrial/technological content, matched
against the sentence text (not the legacy frame_* dictionary scores). This is a coarse topical
filter, not a recognition classifier -- it only decides whether a sentence is ABOUT the kind of
content this project needs, before any R0-R5 label is assigned.

Output: data/annotations/kor_chn_recognition_sample.csv -- document id, text, context, date,
source, empty human-label fields, per the brief's annotation-interface spec (Section 5.4).
"""
import re

import pandas as pd

from srl.utils.config import get_path
from srl.utils.paths import project_root

KEYWORDS = [
    "경제", "산업", "기술", "수출", "수입", "무역", "시장", "경쟁력", "경쟁",
    "반도체", "조선", "배터리", "이차전지", "선박", "제조업", "첨단",
    "투자", "기업", "공급망", "혁신", "성장", "개발도상국", "선진국", "추격", "추월",
    "우위", "격차", "역전", "앞서", "뒤처", "따라잡",
]
KEYWORD_RE = re.compile("|".join(re.escape(k) for k in KEYWORDS))

N_TARGET = 300
YEAR_BUCKETS = [(1988, 1999), (2000, 2009), (2010, 2016), (2017, 2026)]


def main() -> None:
    s = pd.read_parquet(get_path("data.interim") / "pilot" / "partner_sentences.parquet")
    chn = s[(s["partner"] == "CHN") & (s["year"].notna())].copy()
    chn["year"] = chn["year"].astype(int)
    chn["relevant"] = chn["text"].str.contains(KEYWORD_RE)
    rel = chn[chn["relevant"]].copy()
    print(f"CHN sentences total: {len(chn)}; economic/industrial-relevant: {len(rel)} "
          f"({100*len(rel)/len(chn):.1f}%)")

    rng_seed = 20261014
    frames = []
    per_bucket = N_TARGET // len(YEAR_BUCKETS)
    for lo, hi in YEAR_BUCKETS:
        bucket = rel[(rel["year"] >= lo) & (rel["year"] <= hi)]
        n = min(per_bucket, len(bucket))
        if n == 0:
            print(f"  WARNING: no relevant sentences in {lo}-{hi}")
            continue
        take = bucket.sample(n=n, random_state=rng_seed)
        frames.append(take)
        print(f"  {lo}-{hi}: sampled {len(take)} of {len(bucket)} relevant sentences")

    sample = pd.concat(frames).drop_duplicates(subset=["doc_id", "sent_idx"])
    sample = sample.sort_values(["year", "source_id", "doc_id", "sent_idx"])

    out = pd.DataFrame({
        "item_id": [f"korchn_{i:04d}" for i in range(len(sample))],
        "case": "kor_chn",
        "incumbent": "KOR",
        "challenger": "CHN",
        "doc_id": sample["doc_id"].to_numpy(),
        "source_id": sample["source_id"].to_numpy(),
        "institution": sample["institution"].to_numpy(),
        "date": sample["date"].to_numpy(),
        "year": sample["year"].to_numpy(),
        "language": sample["language"].to_numpy(),
        "text": sample["text"].to_numpy(),
        # empty fields for human coding, per brief Section 5.4 -- never pre-filled here
        "human_label_R": "",
        "human_label_dismissive": "",
        "human_label_stereotyping": "",
        "human_label_threat_coexists": "",
        "human_coder_id": "",
        "human_coding_date": "",
        "human_coding_notes": "",
    })
    out_path = project_root() / "data" / "annotations" / "kor_chn_recognition_sample.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nwrote {len(out)} items to {out_path}")
    print(out["year"].value_counts().sort_index())


if __name__ == "__main__":
    main()
