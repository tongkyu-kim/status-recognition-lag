"""Build the clean Japan Diet speech table from raw NDL API JSON (acq_jp_diet_fulltext.py).

Deduplicates across the three queries (a speech can match more than one), parses date/house/
committee/speaker metadata, and writes one parquet table -- the Japan-side analogue of
data/interim/prelim/gov_documents_korea.csv, at document (speech) granularity.

Added 2026-10-14 (overnight execution). First build of this source as full text.
"""
import glob
import json
import sys

import pandas as pd

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from srl.utils.config import get_path


def main() -> None:
    raw_dir = get_path("data.raw") / "jp_diet" / "2026-10-14" / "fulltext"
    rows = []
    for f in glob.glob(str(raw_dir / "*.json")):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        for r in d.get("speechRecord") or []:
            rows.append({
                "speech_id": r.get("speechID"),
                "issue_id": r.get("issueID"),
                "session": r.get("session"),
                "house": r.get("nameOfHouse"),
                "committee": r.get("nameOfMeeting"),
                "issue": r.get("issue"),
                "date": r.get("date"),
                "speaker": r.get("speaker"),
                "speaker_group": r.get("speakerGroup"),
                "speaker_role": r.get("speakerRole"),
                "text": r.get("speech"),
            })
    df = pd.DataFrame(rows).drop_duplicates(subset=["speech_id"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = df["date"].dt.year
    df = df[df["text"].notna() & (df["text"].str.len() > 0)]
    print(f"raw speech records (deduplicated): {len(df)}")
    print(f"year range: {df['year'].min()}-{df['year'].max()}")
    print(df["house"].value_counts())

    out = get_path("data.interim") / "text"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "jp_diet_speeches.parquet", index=False)
    print(f"wrote {len(df)} speeches to {out / 'jp_diet_speeches.parquet'}")


if __name__ == "__main__":
    main()
