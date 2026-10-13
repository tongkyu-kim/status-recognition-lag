"""Build an Excel-friendly manual-review sheet for the YouTube frame (no API calls).

Output: data/processed/youtube_frame/review_sheet.csv (UTF-8 with BOM, opens in Excel).
Fill `decision` (include / exclude) and `reason`, put your initials in `reviewer`, then SAVE A COPY as
data/raw/human_coding/<YYYY-MM-DD>/youtube_frame_review.csv (keep the columns). The next
`run_frame.py collect` applies the decisions, freezes ready country x period samples and downloads
their comments. Decide from title and description only (comments are not downloaded yet).

Guidance (protocol v3): include when the video substantively reports on the country (events,
policy, economy, people or places there as the story's subject); exclude when the country is only a
venue, a passing reference, or one item in a programme rundown.
"""

import json
import re

import _bootstrap  # noqa: F401
import pandas as pd

from srl.youtube import frame


def main() -> None:
    out = frame.out_dir()
    uni = pd.read_csv(out / "video_universe.csv")
    rev = uni[uni["status"] == "manual_review"].copy()
    meta = {}
    for f in (frame.cache_root() / "videos").glob("*.json"):
        for it in json.loads(f.read_text(encoding="utf-8")).get("items", []):
            meta[it["id"]] = it["snippet"]
    names = {k: v["title_include"] for k, v in frame.cfg()["countries"].items()}

    def context(vid: str, iso: str) -> str:
        d = re.sub(r"\s+", " ", meta.get(vid, {}).get("description", ""))
        pos = min((i for i in (d.find(n) for n in names[iso]) if i >= 0), default=-1)
        return d[max(0, pos - 120): pos + 160] if pos >= 0 else d[:280]

    rev["description_context"] = [context(v, c) for v, c in zip(rev["video_id"], rev["country"], strict=True)]
    rev["url"] = "https://www.youtube.com/watch?v=" + rev["video_id"]
    rev["decision"] = ""
    rev["reason"] = ""
    rev["reviewer"] = ""
    cols = ["video_id", "country", "period", "channel", "published_at", "title", "description_context", "url",
            "decision", "reason", "reviewer"]
    sheet = rev.sort_values(["country", "period", "published_at"])[cols]
    sheet.to_csv(out / "review_sheet.csv", index=False, encoding="utf-8-sig")
    print(f"{len(sheet)} videos -> {out / 'review_sheet.csv'}")
    print(sheet.groupby(["country", "period"]).size().to_string())


if __name__ == "__main__":
    main()
