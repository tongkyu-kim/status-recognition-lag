"""search.list for every SearchSpec -> data/raw/youtube/<date>/search/<spec_id>_pN.json.

Each saved file is the API response plus ``_request`` (endpoint/params without the key) and
``_spec`` (country, family, query, order, year slice). search.list costs 100 units per page and
returns at most ~500 results per query in total (pagination limit); results are relevance-ranked,
not a random sample - see the selection-bias section of docs/youtube_data_design.md.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict

from srl.utils.config import load_config
from srl.youtube.api import QuotaExhausted, YouTubeClient, raw_root, save_yt
from srl.youtube.queries import SearchSpec

logger = logging.getLogger(__name__)


def run_search(client: YouTubeClient, plan: list[SearchSpec], *, max_pages: int = 1) -> dict:
    defaults = load_config("youtube_queries")["defaults"]
    done = skipped = 0
    for spec in plan:
        token = None
        for page in range(1, max_pages + 1):
            rel = f"search/{spec.spec_id}_p{page}.json"
            if (raw_root() / rel).exists():
                body = json.loads((raw_root() / rel).read_text(encoding="utf-8"))
                token = body.get("nextPageToken")
                skipped += 1
                if not token:
                    break
                continue
            params = {
                "part": "snippet",
                "q": spec.query,
                "type": defaults["type"],
                "maxResults": 50,
                "order": spec.order,
                "regionCode": defaults["regionCode"],
                "relevanceLanguage": defaults["relevanceLanguage"],
                "safeSearch": defaults["safeSearch"],
            }
            if spec.published_after:
                params["publishedAfter"] = spec.published_after
            if spec.published_before:
                params["publishedBefore"] = spec.published_before
            if token:
                params["pageToken"] = token
            try:
                body = client.call("search", note=f"{spec.country}|{spec.query}", **params)
            except QuotaExhausted:
                logger.warning("Quota budget reached after %d searches; rerun tomorrow (resumable).", done)
                return {"done": done, "skipped": skipped, "stopped": "quota"}
            body["_spec"] = asdict(spec) | {"spec_id": spec.spec_id, "page": page}
            save_yt(
                rel,
                json.dumps(body, ensure_ascii=False),
                url="search.list",
                http_status=200,
                notes=f"{spec.country} {spec.family} {spec.query!r} p{page}",
            )
            done += 1
            token = body.get("nextPageToken")
            if not token:
                break
    return {"done": done, "skipped": skipped, "stopped": None}
