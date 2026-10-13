# -*- coding: utf-8 -*-
"""Build a stratified, economic/industrial-relevance-filtered sample of Japan->Korea passages for
R0-R5 recognition classification, from the newly built jp_diet speech corpus
(scripts/acquire/build_jp_diet_corpus.py). Mirrors sample_recognition_passages.py (kor_chn case).

Output: data/annotations/jpn_kor_recognition_sample.csv
"""
import sys

import pandas as pd

from srl.text.segmentation import split_sentences_ja
from srl.utils.config import get_path
from srl.utils.paths import project_root

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

KEYWORDS = [
    "経済", "産業", "技術", "輸出", "輸入", "貿易", "市場", "競争力", "競争",
    "半導体", "造船", "バッテリー", "電池", "製造業", "先端",
    "投資", "企業", "成長", "先進国", "開発途上国", "途上国", "追い上げ", "追い越し", "追いつ",
    "優位", "格差", "逆転", "遅れ", "水準",
]


def is_korea_sentence(s: str) -> bool:
    return "韓国" in s


def is_relevant(s: str) -> bool:
    return any(k in s for k in KEYWORDS)


N_TARGET = 200
YEAR_BUCKETS = [(1980, 1994), (1995, 2005), (2006, 2015), (2016, 2024)]


def main() -> None:
    speeches = pd.read_parquet(get_path("data.interim") / "text" / "jp_diet_speeches.parquet")
    speeches = speeches[speeches["year"].notna()].copy()
    speeches["year"] = speeches["year"].astype(int)

    rows = []
    for _, doc in speeches.iterrows():
        for i, sent in enumerate(split_sentences_ja(doc["text"], min_chars=8)):
            if len(sent) > 400:
                sent = sent[:400]
            if is_korea_sentence(sent) and is_relevant(sent):
                rows.append({
                    "speech_id": doc["speech_id"], "sent_idx": i, "date": doc["date"],
                    "year": doc["year"], "house": doc["house"], "committee": doc["committee"],
                    "speaker": doc["speaker"], "speaker_group": doc["speaker_group"], "text": sent,
                })
    rel = pd.DataFrame(rows).drop_duplicates(subset=["speech_id", "sent_idx"])
    print(f"Korea-mentioning + economic/industrial-relevant JP Diet sentences: {len(rel)}")
    print(rel.groupby((rel["year"] // 5) * 5).size())

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
        print(f"  {lo}-{hi}: sampled {len(take)} of {len(bucket)}")

    sample = pd.concat(frames).drop_duplicates(subset=["speech_id", "sent_idx"])
    sample = sample.sort_values(["year", "speech_id", "sent_idx"])

    out = pd.DataFrame({
        "item_id": [f"jpnkor_{i:04d}" for i in range(len(sample))],
        "case": "jpn_kor",
        "incumbent": "JPN",
        "challenger": "KOR",
        "doc_id": sample["speech_id"].to_numpy(),
        "source_id": "jp_diet",
        "institution": sample["house"].to_numpy(),
        "date": sample["date"].astype(str).to_numpy(),
        "year": sample["year"].to_numpy(),
        "language": "ja",
        "speaker": sample["speaker"].to_numpy(),
        "speaker_group": sample["speaker_group"].to_numpy(),
        "text": sample["text"].to_numpy(),
        "human_label_R": "", "human_label_dismissive": "", "human_label_stereotyping": "",
        "human_label_threat_coexists": "", "human_coder_id": "", "human_coding_date": "",
        "human_coding_notes": "",
    })
    out_path = project_root() / "data" / "annotations" / "jpn_kor_recognition_sample.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nwrote {len(out)} items to {out_path}")
    print(out["year"].value_counts().sort_index())


if __name__ == "__main__":
    main()
