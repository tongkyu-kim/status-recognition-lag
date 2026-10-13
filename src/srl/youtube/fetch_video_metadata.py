"""videos.list and channels.list for every video/channel found by search.

Raw: data/raw/youtube/<date>/videos/batch_<first_id>.json (<= 50 ids per call, 1 unit) and
     data/raw/youtube/<date>/channels/batch_<first_id>.json.
Videos that are deleted/private at retrieval time are simply absent from the response; they are
recorded in the interim table with ``available = False`` (see srl.youtube.tables).
"""

from __future__ import annotations

import json
import logging

from srl.youtube.api import QuotaExhausted, YouTubeClient, raw_root, save_yt

logger = logging.getLogger(__name__)
VIDEO_PARTS = "snippet,statistics,contentDetails,topicDetails,status,localizations"
CHANNEL_PARTS = "snippet,statistics,topicDetails,brandingSettings,status"


def ids_from_search() -> list[str]:
    ids = []
    for f in sorted((raw_root() / "search").glob("*.json")):
        for it in json.loads(f.read_text(encoding="utf-8")).get("items", []):
            vid = it.get("id", {}).get("videoId")
            if vid:
                ids.append(vid)
    return list(dict.fromkeys(ids))


def _fetched(folder: str, key: str) -> set[str]:
    got = set()
    for f in (raw_root() / folder).glob("*.json"):
        got.update(json.loads(f.read_text(encoding="utf-8")).get("_requested", []))
    return got


def _batched(client: YouTubeClient, endpoint: str, parts: str, ids: list[str], folder: str) -> int:
    done = _fetched(folder, "id")
    todo = [i for i in ids if i not in done]
    n = 0
    for k in range(0, len(todo), 50):
        batch = todo[k : k + 50]
        try:
            body = client.call(
                endpoint, note=f"{len(batch)} ids", part=parts, id=",".join(batch), maxResults=50
            )
        except QuotaExhausted:
            logger.warning("Quota budget reached during %s; rerun later (resumable).", endpoint)
            break
        body["_requested"] = batch
        save_yt(
            f"{folder}/batch_{batch[0]}.json",
            json.dumps(body, ensure_ascii=False),
            url=f"{endpoint}.list",
            http_status=200,
            notes=f"{len(batch)} requested",
        )
        n += 1
    return n


def fetch_videos(client: YouTubeClient) -> int:
    return _batched(client, "videos", VIDEO_PARTS, ids_from_search(), "videos")


def fetch_channels(client: YouTubeClient) -> int:
    ids = []
    for f in (raw_root() / "videos").glob("*.json"):
        ids += [
            it["snippet"]["channelId"] for it in json.loads(f.read_text(encoding="utf-8")).get("items", [])
        ]
    return _batched(client, "channels", CHANNEL_PARTS, list(dict.fromkeys(ids)), "channels")
