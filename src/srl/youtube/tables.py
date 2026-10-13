"""Flatten raw YouTube API responses into interim tables and coverage diagnostics.

Outputs (data/interim/youtube/):
    video_query_links.parquet  one row per (video, search spec) - retrieval provenance
    videos.parquet             one row per video (metadata; video_frame left empty for coding)
    comments.parquet           one row per comment (hashed author; no display names)
Diagnostics (outputs/diagnostics/):
    youtube_coverage.csv, youtube_frame_coverage.csv, youtube_query_yield.csv
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from srl.utils.config import get_path

_HANGUL = re.compile(r"[가-힣]")
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)
_DUR = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def hangul_share(text: str | None) -> float:
    """Share of letters that are Hangul syllables (NaN if no letters)."""
    if not text:
        return np.nan
    letters = _LETTER.findall(text)
    return len(_HANGUL.findall(text)) / len(letters) if letters else np.nan


def is_korean(text: str | None, threshold: float = 0.5) -> bool:
    share = hangul_share(text)
    return bool(share >= threshold and len(_HANGUL.findall(text or "")) >= 2) if share == share else False


def iso_duration_seconds(value: str | None) -> float:
    m = _DUR.fullmatch(value or "")
    if not m:
        return np.nan
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _load(folder: Path) -> list[dict]:
    return (
        [json.loads(f.read_text(encoding="utf-8")) for f in sorted(folder.glob("*.json"))]
        if folder.exists()
        else []
    )


def build_link_table(run_dir: Path) -> pd.DataFrame:
    rows = []
    for body in _load(run_dir / "search"):
        spec = body.get("_spec", {})
        for rank, it in enumerate(body.get("items", []), start=1):
            vid = it.get("id", {}).get("videoId")
            if vid:
                rows.append(
                    {
                        "video_id": vid,
                        "spec_id": spec.get("spec_id"),
                        "country": spec.get("country"),
                        "family": spec.get("family"),
                        "query": spec.get("query"),
                        "order": spec.get("order"),
                        "year_slice": spec.get("published_after", "")[:4] or "all",
                        "page": spec.get("page"),
                        "rank": rank,
                        "total_results_est": body.get("pageInfo", {}).get("totalResults"),
                    }
                )
    return pd.DataFrame(rows)


def build_video_table(run_dir: Path, links: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for body in _load(run_dir / "videos"):
        for it in body.get("items", []):
            sn, st, cd = it.get("snippet", {}), it.get("statistics", {}), it.get("contentDetails", {})
            text = f"{sn.get('title', '')}\n{sn.get('description', '')}"
            rows.append(
                {
                    "video_id": it["id"],
                    "title": sn.get("title"),
                    "description": sn.get("description"),
                    "published_at": sn.get("publishedAt"),
                    "channel_id": sn.get("channelId"),
                    "channel_title": sn.get("channelTitle"),
                    "category_id": sn.get("categoryId"),
                    "tags": "|".join(sn.get("tags", [])),
                    "default_language": sn.get("defaultLanguage"),
                    "default_audio_language": sn.get("defaultAudioLanguage"),
                    "view_count": pd.to_numeric(st.get("viewCount"), errors="coerce"),
                    "like_count": pd.to_numeric(st.get("likeCount"), errors="coerce"),
                    "comment_count": pd.to_numeric(st.get("commentCount"), errors="coerce"),
                    "duration_s": iso_duration_seconds(cd.get("duration")),
                    "caption_flag": cd.get("caption"),
                    "topic_categories": "|".join(it.get("topicDetails", {}).get("topicCategories", [])),
                    "made_for_kids": it.get("status", {}).get("madeForKids"),
                    "hangul_share_meta": hangul_share(text),
                    "url": f"https://www.youtube.com/watch?v={it['id']}",
                    "available": True,
                    "retrieved_utc": body.get("_request", {}).get("retrieved_utc"),
                }
            )
    videos = pd.DataFrame(rows)
    if not links.empty:
        requested = set(links["video_id"])
        missing = requested - set(videos.get("video_id", pd.Series(dtype=str)))
        if missing:  # deleted/private between search and videos.list
            videos = pd.concat(
                [videos, pd.DataFrame({"video_id": sorted(missing), "available": False})], ignore_index=True
            )
        prov = (
            links.groupby("video_id")
            .agg(
                countries=("country", lambda s: "|".join(sorted(set(s)))),
                families=("family", lambda s: "|".join(sorted(set(s)))),
                queries=("query", lambda s: "|".join(sorted(set(s)))),
                n_query_hits=("spec_id", "nunique"),
                best_rank=("rank", "min"),
            )
            .reset_index()
        )
        videos = videos.merge(prov, on="video_id", how="left")
        videos["n_countries"] = videos["countries"].str.count(r"\|") + 1
    if "published_at" in videos:
        videos["year"] = pd.to_datetime(videos["published_at"], errors="coerce", utc=True).dt.year
    caps = {}
    for f in (
        (run_dir / "transcripts").glob("*_captions_list.json") if (run_dir / "transcripts").exists() else []
    ):
        body = json.loads(f.read_text(encoding="utf-8"))
        tracks = body.get("items", [])
        caps[f.name.split("_captions_list")[0]] = {
            "caption_tracks": len(tracks),
            "caption_langs": "|".join(sorted({t["snippet"].get("language", "") for t in tracks})),
            "caption_manual_ko": any(
                t["snippet"].get("language", "").startswith("ko") and t["snippet"].get("trackKind") != "asr"
                for t in tracks
            ),
        }
    if caps:
        videos = videos.merge(
            pd.DataFrame.from_dict(caps, orient="index").rename_axis("video_id").reset_index(),
            on="video_id",
            how="left",
        )
    videos["transcript_text_available"] = False  # official API cannot return third-party captions
    videos["video_frame"] = pd.NA  # human-coded later (docs/youtube_coding_protocol.md)
    return videos


def build_comment_table(run_dir: Path) -> pd.DataFrame:
    rows = []
    root = run_dir / "comments"
    if not root.exists():
        return pd.DataFrame()

    def add(c: dict, video_id: str, parent: str | None, thread_reply_count=None) -> None:
        sn = c.get("snippet", {})
        text = sn.get("textOriginal") or sn.get("textDisplay") or ""
        rows.append(
            {
                "comment_id": c["id"],
                "video_id": video_id,
                "parent_comment_id": parent,
                "is_reply": parent is not None,
                "text": text,
                "published_at": sn.get("publishedAt"),
                "updated_at": sn.get("updatedAt"),
                "like_count": sn.get("likeCount"),
                "reply_count": thread_reply_count,
                "author_hash": sn.get("authorHash"),
                "hangul_share": hangul_share(text),
                "is_korean": is_korean(text),
            }
        )

    for vdir in sorted(p for p in root.iterdir() if p.is_dir()):
        for f in sorted(vdir.glob("threads_p*.json")):
            for th in json.loads(f.read_text(encoding="utf-8")).get("items", []):
                top = th["snippet"]["topLevelComment"]
                add(top, vdir.name, None, th["snippet"].get("totalReplyCount"))
                for rep in th.get("replies", {}).get("comments", []):
                    add(rep, vdir.name, top["id"])
        for f in sorted(vdir.glob("replies_*.json")):
            for rep in json.loads(f.read_text(encoding="utf-8")).get("items", []):
                add(rep, vdir.name, rep["snippet"].get("parentId"))
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates("comment_id")  # embedded replies re-fetched via comments.list
        df["year"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True).dt.year
    return df


COVERAGE_COLUMNS = [
    "country",
    "year",
    "n_videos",
    "n_comments",
    "n_channels",
    "median_comments_per_video",
    "korean_comment_share",
    "status_relevant_share",
    "duplicate_comment_rate",
    "note",
]


def coverage_tables(
    videos: pd.DataFrame, comments: pd.DataFrame, links: pd.DataFrame, countries: list[str], note: str = ""
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Country-year and country-frame coverage. ``status_relevant_share`` stays NaN until coded."""
    if videos.empty or links.empty:
        cov = pd.DataFrame(
            [
                {
                    "country": c,
                    "year": pd.NA,
                    "n_videos": 0,
                    "n_comments": 0,
                    "n_channels": 0,
                    "median_comments_per_video": np.nan,
                    "korean_comment_share": np.nan,
                    "status_relevant_share": np.nan,
                    "duplicate_comment_rate": np.nan,
                    "note": note,
                }
                for c in countries
            ],
            columns=COVERAGE_COLUMNS,
        )
        frames = pd.DataFrame(
            [
                {
                    "country": c,
                    "frame": "uncoded",
                    "retrieval_family": pd.NA,
                    "n_videos": 0,
                    "n_comments": 0,
                    "note": note,
                }
                for c in countries
            ]
        )
        return cov, frames
    vc = (
        links[["video_id", "country", "family"]]
        .drop_duplicates()
        .merge(videos[["video_id", "year", "channel_id", "video_frame"]], on="video_id", how="left")
    )
    if comments.empty:
        per_video = pd.DataFrame(columns=["video_id", "n_comments", "n_korean", "n_dup"])
    else:  # expects duplicate flags from srl.youtube.deduplicate.flag_duplicates
        dup = comments["dup_within_video"] | comments["dup_same_author_cross_video"]
        per_video = (
            comments.assign(_dup=dup)
            .groupby("video_id")
            .agg(n_comments=("comment_id", "size"), n_korean=("is_korean", "sum"), n_dup=("_dup", "sum"))
            .reset_index()
        )
    vcy = (
        vc.drop_duplicates(["video_id", "country"])
        .merge(per_video, on="video_id", how="left")
        .fillna({"n_comments": 0, "n_korean": 0, "n_dup": 0})
    )
    cov = (
        vcy.groupby(["country", "year"])
        .agg(
            n_videos=("video_id", "nunique"),
            n_comments=("n_comments", "sum"),
            n_channels=("channel_id", "nunique"),
            median_comments_per_video=("n_comments", "median"),
            n_korean=("n_korean", "sum"),
            n_dup=("n_dup", "sum"),
        )
        .reset_index()
    )
    cov["korean_comment_share"] = cov["n_korean"] / cov["n_comments"].replace(0, np.nan)
    cov["duplicate_comment_rate"] = cov["n_dup"] / cov["n_comments"].replace(0, np.nan)
    cov["status_relevant_share"] = np.nan  # requires human coding (pilot stage 1)
    cov["note"] = note
    frames = (
        vc.assign(frame=vc["video_frame"].fillna("uncoded"))
        .drop_duplicates(["video_id", "country", "family"])
        .merge(per_video, on="video_id", how="left")
        .groupby(["country", "frame", "family"])
        .agg(n_videos=("video_id", "nunique"), n_comments=("n_comments", "sum"))
        .reset_index()
        .rename(columns={"family": "retrieval_family"})
    )
    frames["note"] = note
    return cov[COVERAGE_COLUMNS], frames


def interim_dir() -> Path:
    path = get_path("data.interim") / "youtube"
    path.mkdir(parents=True, exist_ok=True)
    return path
