"""PILOT stage 1: sentence-level partner attribution and recognition-frame scoring.

Exploratory only. The frame dictionary (config/recognition_frames.yaml) is a CANDIDATE baseline,
not yet validated against human coding (docs/coding_protocol.md); results are indicative.

Input : data/interim/prelim/gov_documents_korea.csv + data/interim/text/gov_documents_korea_text.parquet
Output: data/interim/pilot/partner_sentences.parquet   one row per (sentence, partner mentioned)
        data/interim/pilot/frames_partner_year.csv     partner x year x source aggregates
        outputs/pilot/kwic_frame_samples.csv           random matched sentences per frame (precision check)

Rules: documents with an unreliable date (MOTIR legacy releases without recovered dates) are dropped;
a sentence counts for partner j if the entity matcher finds j in it (shields applied; ASEAN group
mentions are not allocated to members); frames are counted in that sentence.
"""

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from srl.recognition.dictionary import compile_frames, load_frame_dictionary, score_text  # noqa: E402
from srl.text.entities import default_matcher  # noqa: E402
from srl.text.segmentation import split_sentences  # noqa: E402
from srl.utils.config import get_path  # noqa: E402

PARTNERS = ["BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "TLS", "VNM", "CHN"]
_COMPILED = None


def _work(rows: list[tuple[str, str]]) -> list[dict]:
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = compile_frames(load_frame_dictionary())
    matcher = default_matcher()
    out = []
    for doc_id, text in rows:
        for k, sent in enumerate(split_sentences(text, min_chars=5)):
            if len(sent) > 2000:  # tables / run-on blocks
                sent = sent[:2000]
            isos = {m.entity_id for m in matcher.find(sent) if m.entity_type == "country"} & set(PARTNERS)
            if not isos:
                continue
            sc = score_text(sent, _COMPILED)
            base = {"doc_id": doc_id, "sent_idx": k, "text": sent,
                    "n_partners_in_sentence": len(isos),
                    "frame_vertical": sc.get("frame_vertical", 0),
                    "frame_horizontal": sc.get("frame_horizontal", 0),
                    "frame_competitive": sc.get("frame_competitive", 0),
                    "subframes": "|".join(sorted(k2[4:] for k2 in sc if k2.startswith("sub_")))}
            out += [{**base, "partner": iso} for iso in sorted(isos)]
    return out


def main() -> None:
    pre = get_path("data.interim") / "prelim"
    meta = pd.read_csv(pre / "gov_documents_korea.csv", low_memory=False,
                       usecols=["doc_id", "source_id", "institution", "doc_type", "language", "year", "date",
                                "date_reliable", "partners_mentioned", "is_cross_source_duplicate"])
    text = pd.read_parquet(get_path("data.interim") / "text" / "gov_documents_korea_text.parquet")
    docs = meta.merge(text[["doc_id", "text"]], on="doc_id")
    keep = docs["partners_mentioned"].fillna("").ne("") & docs["year"].notna()
    keep &= (docs["date_reliable"].astype(str) != "False") & ~docs["is_cross_source_duplicate"].astype(bool)
    docs = docs[keep]
    print(f"documents with text and partner mentions: {len(docs)}")
    rows = list(zip(docs["doc_id"], docs["text"], strict=True))
    chunks = [rows[i:i + 200] for i in range(0, len(rows), 200)]
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1)) as ex:
        results = [r for part in ex.map(_work, chunks) for r in part]
    sent = pd.DataFrame(results).merge(docs.drop(columns="text"), on="doc_id", how="left")
    out = get_path("data.interim") / "pilot"
    out.mkdir(parents=True, exist_ok=True)
    sent.to_parquet(out / "partner_sentences.parquet", index=False)
    print(f"partner-sentences: {len(sent)}")

    for f in ("vertical", "horizontal", "competitive"):
        sent[f"has_{f}"] = sent[f"frame_{f}"] > 0
    agg = sent.groupby(["partner", "year", "source_id"]).agg(
        n_sentences=("text", "size"), n_docs=("doc_id", "nunique"),
        V=("frame_vertical", "sum"), H=("frame_horizontal", "sum"), C=("frame_competitive", "sum"),
        sent_V=("has_vertical", "sum"), sent_H=("has_horizontal", "sum"), sent_C=("has_competitive", "sum"),
    ).reset_index()
    agg.to_csv(out / "frames_partner_year.csv", index=False)

    rng = np.random.default_rng(20260930)
    samples = []
    for f in ("vertical", "horizontal", "competitive"):
        hits = sent[sent[f"has_{f}"]]
        take = hits.iloc[rng.choice(len(hits), size=min(40, len(hits)), replace=False)] if len(hits) else hits
        samples.append(take.assign(frame=f)[["frame", "partner", "year", "source_id", "subframes", "text"]])
    kw = get_path("outputs.diagnostics").parent / "pilot"
    kw.mkdir(parents=True, exist_ok=True)
    pd.concat(samples).to_csv(kw / "kwic_frame_samples.csv", index=False, encoding="utf-8-sig")
    print(agg.groupby("partner")[["n_sentences", "sent_V", "sent_H", "sent_C"]].sum().to_string())


if __name__ == "__main__":
    main()
