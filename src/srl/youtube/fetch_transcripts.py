"""Transcript AVAILABILITY via the official API; no transcript text is retrieved automatically.

Why: the Data API's ``captions.download`` requires OAuth authorization by the video's OWNER (or
the owner allowing third-party contributions). For third-party videos, lawful programmatic
retrieval of caption text is therefore not available through the official API, and unofficial
libraries that scrape the player's timed-text endpoint are out of scope (project rule: official
API only, no HTML scraping). ``captions.list`` (50 units per video) tells us whether caption
tracks exist, their language and whether they are auto-generated (``trackKind == 'asr'``).

Consequences for the design (docs/youtube_data_design.md): video frames are coded from title +
description (+ transcript where a human obtains it manually, docs/youtube_manual_tasks.md Y4).
Raw: data/raw/youtube/<date>/transcripts/<video_id>_captions_list.json
"""

from __future__ import annotations

import json
import logging

from srl.youtube.api import QuotaExhausted, YouTubeAPIError, YouTubeClient, raw_root, save_yt

logger = logging.getLogger(__name__)


def fetch_caption_availability(client: YouTubeClient, video_ids: list[str]) -> int:
    n = 0
    for vid in video_ids:
        rel = f"transcripts/{vid}_captions_list.json"
        if (raw_root() / rel).exists():
            continue
        try:
            body = client.call("captions", note=vid, part="snippet", videoId=vid)
        except QuotaExhausted:
            logger.warning("Quota budget reached after %d caption lists.", n)
            break
        except YouTubeAPIError as exc:
            body = {"error": exc.reason, "status": exc.status}
        save_yt(rel, json.dumps(body, ensure_ascii=False), url="captions.list", http_status=200, log=False)
        n += 1
    return n
