"""commentThreads.list (+ comments.list for replies) for selected videos.

- Comment text is requested as ``textOriginal`` (plain text, no HTML) and ``textDisplay``.
- Commenter identity fields are removed / hashed BEFORE saving (srl.youtube.api.minimize_*).
- Per-video cap: ``comments.max_top_level_per_video`` (collection) - analytic caps are applied later
  by srl.youtube.sample_comments. The cap and the ``order`` used are stored in each file.
- Videos with comments disabled return 403 ``commentsDisabled``; this is recorded, not retried.
Raw: data/raw/youtube/<date>/comments/<video_id>/threads_pNNN.json, replies_<thread>_pNNN.json
"""

from __future__ import annotations

import json
import logging

import pandas as pd

from srl.acquisition.fetch import log_download
from srl.youtube.api import (
    SOURCE_ID,
    QuotaExhausted,
    YouTubeAPIError,
    YouTubeClient,
    hash_salt,
    minimize_comment_resource,
    raw_root,
    save_yt,
    settings,
)

logger = logging.getLogger(__name__)


def fetch_video_comments(
    client: YouTubeClient,
    video_id: str,
    *,
    max_top_level: int,
    order: str = "relevance",
    fetch_replies: bool = True,
    max_replies: int = 100,
) -> dict:
    salt = hash_salt()
    folder = raw_root() / "comments" / video_id
    if (folder / "_complete.json").exists():
        return {"video_id": video_id, "status": "already_complete"}
    token, page, n_top, status = None, 1, 0, "ok"
    while n_top < max_top_level:
        rel = f"comments/{video_id}/threads_p{page:03d}.json"
        if (raw_root() / rel).exists():
            body = json.loads((raw_root() / rel).read_text(encoding="utf-8"))
        else:
            params = {
                "part": "snippet,replies",
                "videoId": video_id,
                "maxResults": 100,
                "order": order,
                "textFormat": "plainText",
            }
            if token:
                params["pageToken"] = token
            try:
                body = client.call("commentThreads", note=video_id, **params)
            except YouTubeAPIError as exc:
                status = exc.reason or f"http_{exc.status}"
                log_download(
                    SOURCE_ID,
                    f"commentThreads.list?videoId={video_id}",
                    http_status=exc.status,
                    outcome="unavailable",
                    notes=status,
                )
                break
            body["items"] = [minimize_comment_resource(it, salt) for it in body.get("items", [])]
            body["_collection_rule"] = {"order": order, "max_top_level_per_video": max_top_level}
            save_yt(
                rel,
                json.dumps(body, ensure_ascii=False),
                url="commentThreads.list",
                http_status=200,
                notes=f"{video_id} page {page}",
            )
        items = body.get("items", [])
        n_top += len(items)
        if fetch_replies:
            for th in items:
                total = th["snippet"].get("totalReplyCount", 0)
                embedded = len(th.get("replies", {}).get("comments", []))
                if total > embedded:
                    _fetch_replies(client, video_id, th["id"], max_replies, salt)
        token = body.get("nextPageToken")
        page += 1
        if not token:
            break
    save_yt(
        f"comments/{video_id}/_complete.json",
        json.dumps(
            {
                "video_id": video_id,
                "status": status,
                "n_top_level": n_top,
                "order": order,
                "cap": max_top_level,
            }
        ),
        log=False,
    )
    return {"video_id": video_id, "status": status, "n_top_level": n_top}


def _fetch_replies(
    client: YouTubeClient, video_id: str, thread_id: str, max_replies: int, salt: bytes
) -> None:
    token, page, n = None, 1, 0
    while n < max_replies:
        rel = f"comments/{video_id}/replies_{thread_id}_p{page:02d}.json"
        if (raw_root() / rel).exists():
            body = json.loads((raw_root() / rel).read_text(encoding="utf-8"))
        else:
            params = {"part": "snippet", "parentId": thread_id, "maxResults": 100, "textFormat": "plainText"}
            if token:
                params["pageToken"] = token
            body = client.call("comments", note=thread_id, **params)
            body["items"] = [minimize_comment_resource(it, salt) for it in body.get("items", [])]
            save_yt(
                rel, json.dumps(body, ensure_ascii=False), url="comments.list", http_status=200, log=False
            )
        n += len(body.get("items", []))
        token = body.get("nextPageToken")
        page += 1
        if not token:
            break


def fetch_comments_for(client: YouTubeClient, video_ids: list[str], *, pilot: bool) -> list[dict]:
    cfg = settings()["comments"]
    cap = cfg["pilot_max_top_level_per_video"] if pilot else cfg["max_top_level_per_video"]
    results = []
    for vid in video_ids:
        try:
            results.append(
                fetch_video_comments(
                    client,
                    vid,
                    max_top_level=cap,
                    order=cfg["order"],
                    fetch_replies=cfg["fetch_replies"],
                    max_replies=cfg["max_replies_per_thread"],
                )
            )
        except QuotaExhausted:
            logger.warning("Quota budget reached; %d videos done. Rerun later (resumable).", len(results))
            break
    return results


def select_videos(per_country: int | None = None) -> list[str]:
    """Videos to collect comments for.

    Full run (``per_country=None``): every available video with comments that passes the content
    screen. Pilot: the ``pilot_per_year_bin`` most-commented screened videos per country x year bin.
    The screen (country named + economic/status vocabulary in title+description) is defined in
    config/youtube_sampling.yaml -> comments.selection and is recorded with the corpus.
    """
    import re

    from srl.utils.config import load_config
    from srl.youtube import tables

    sel = settings()["comments"]["selection"]
    links = tables.build_link_table(raw_root())
    if links.empty:
        return []
    videos = tables.build_video_table(raw_root(), links)
    videos = videos[videos["available"].fillna(False) & (videos["comment_count"].fillna(0) > 0)]
    names = {iso: c["name_ko"] for iso, c in load_config("countries")["countries"].items()}
    vc = links[["video_id", "country"]].drop_duplicates().merge(videos, on="video_id")
    text = vc["title"].fillna("") + " " + vc["description"].fillna("")
    keep = text.str.contains(sel["relevance_pattern"], regex=True)
    if sel.get("require_country_name", True):
        named = [bool(re.search(re.escape(names[c]), t)) for c, t in zip(vc["country"], text, strict=True)]
        keep &= pd.Series(named, index=vc.index)
    vc = vc[keep]
    if per_country is None:
        return list(dict.fromkeys(vc["video_id"]))
    bins = sel["year_bins"]
    vc = vc.assign(year_bin=pd.cut(vc["year"], [b[0] - 0.5 for b in bins] + [bins[-1][1] + 0.5],
                                   labels=[f"{a}-{b}" for a, b in bins]))
    n = int(sel["pilot_per_year_bin"])
    picked = (vc.sort_values("comment_count", ascending=False)
              .groupby(["country", "year_bin"], observed=True).head(n))
    return list(dict.fromkeys(picked["video_id"]))
