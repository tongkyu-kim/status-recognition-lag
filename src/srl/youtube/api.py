"""YouTube Data API v3 client with a persistent quota ledger and privacy minimization.

- The API key is read from the environment variable named in config/youtube_sampling.yaml
  (default ``YOUTUBE_API_KEY``) or from a git-ignored ``.env`` file at the repository root. It is
  never logged or written to disk by this code.
- Every call's documented quota cost is appended to ``metadata/youtube_quota_log.csv``. Calls stop
  (``QuotaExhausted``) before the day's usage would exceed ``daily_quota_units - reserve``. The
  quota day follows Google's reset at midnight US Pacific time.
- Privacy minimization at ingest: commenter display names, profile-image URLs and channel URLs
  are dropped, and commenter channel ids are replaced by a salted HMAC-SHA256 before anything is
  written to disk (data minimization; see docs/youtube_data_design.md, "Ethics"). Video/channel
  metadata of *publishers* is kept, because channel type is an analytical variable.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import logging
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from srl.acquisition.fetch import PoliteSession, log_download, metadata_dir
from srl.utils.config import load_config
from srl.utils.paths import project_root

logger = logging.getLogger(__name__)

SOURCE_ID = "youtube"
PT = ZoneInfo("America/Los_Angeles")  # YouTube quota resets at midnight US Pacific (DST-aware)
AUTHOR_DROP = ("authorDisplayName", "authorProfileImageUrl", "authorChannelUrl")


class MissingCredential(RuntimeError):
    """No API key (or hashing salt) configured - a manual setup task (docs/youtube_manual_tasks.md)."""


class QuotaExhausted(RuntimeError):
    """The configured daily quota budget is used up."""


class YouTubeAPIError(RuntimeError):
    def __init__(self, status: int, reason: str, message: str):
        super().__init__(f"HTTP {status} {reason}: {message}")
        self.status, self.reason = status, reason


def settings() -> dict[str, Any]:
    return load_config("youtube_sampling")


def _dotenv() -> dict[str, str]:
    path = project_root() / ".env"
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_secret(name: str) -> str | None:
    return os.environ.get(name) or _dotenv().get(name)


def api_key() -> str:
    var = settings()["api"]["key_env_var"]
    key = get_secret(var)
    if not key:
        raise MissingCredential(
            f"No YouTube Data API key: set {var} in the environment or in a git-ignored .env file "
            "(see docs/youtube_manual_tasks.md, task Y1)."
        )
    return key


def hash_salt(create: bool = True) -> bytes:
    """Project salt for author-id hashing; created once in the git-ignored .env if absent."""
    var = settings()["privacy"]["salt_env_var"]
    salt = get_secret(var)
    if salt:
        return salt.encode()
    if not create:
        raise MissingCredential(f"No hashing salt ({var}).")
    salt = secrets.token_hex(32)
    env = project_root() / ".env"
    with env.open("a", encoding="utf-8") as fh:
        fh.write(
            "\n# created by srl.youtube.api for author-id hashing; keep private, never commit\n"
            f"{var}={salt}\n"
        )
    os.environ[var] = salt
    logger.warning(
        "Created a new author-id hashing salt in .env (%s). Back it up privately: hashes "
        "are only comparable across runs with the same salt.",
        var,
    )
    return salt.encode()


def hash_author(channel_id: str, salt: bytes) -> str:
    return hmac.new(salt, channel_id.encode(), hashlib.sha256).hexdigest()[:24]


def minimize_comment_resource(item: dict, salt: bytes) -> dict:
    """Drop commenter PII fields in place (comment, commentThread top-level comment and replies)."""

    def scrub(snippet: dict) -> None:
        for k in AUTHOR_DROP:
            snippet.pop(k, None)
        aid = snippet.pop("authorChannelId", None)
        if isinstance(aid, dict) and aid.get("value"):
            snippet["authorHash"] = hash_author(aid["value"], salt)

    if item.get("kind") == "youtube#comment":
        scrub(item.get("snippet", {}))
    elif item.get("kind") == "youtube#commentThread":
        top = item.get("snippet", {}).get("topLevelComment")
        if top:
            scrub(top.get("snippet", {}))
        for rep in item.get("replies", {}).get("comments", []):
            scrub(rep.get("snippet", {}))
    return item


class QuotaLedger:
    COLUMNS = ["timestamp_utc", "quota_day_pt", "endpoint", "units", "note"]

    def __init__(self):
        cfg = settings()["api"]
        self.budget = int(cfg["daily_quota_units"]) - int(cfg["quota_reserve_units"])
        self.costs = cfg["cost"]
        self.path = metadata_dir() / "youtube_quota_log.csv"

    @staticmethod
    def quota_day() -> str:
        return datetime.now(PT).date().isoformat()

    def used_today(self) -> int:
        if not self.path.exists():
            return 0
        day = self.quota_day()
        with self.path.open(encoding="utf-8") as fh:
            return sum(int(r["units"]) for r in csv.DictReader(fh) if r["quota_day_pt"] == day)

    def remaining(self) -> int:
        return self.budget - self.used_today()

    def charge(self, endpoint: str, note: str = "") -> None:
        units = int(self.costs.get(endpoint, 1))
        if self.used_today() + units > self.budget:
            raise QuotaExhausted(f"Daily budget {self.budget} units reached ({endpoint} needs {units}).")
        new = not self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=self.COLUMNS)
            if new:
                w.writeheader()
            w.writerow(
                {
                    "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                    "quota_day_pt": self.quota_day(),
                    "endpoint": endpoint,
                    "units": units,
                    "note": note[:200],
                }
            )


class YouTubeClient:
    """Thin REST client. ``call(endpoint, **params)`` returns the parsed JSON body."""

    def __init__(self, key: str | None = None):
        cfg = settings()["api"]
        self.base = cfg["base_url"].rstrip("/")
        self._key = key or api_key()
        self.ledger = QuotaLedger()
        self.http = PoliteSession(
            SOURCE_ID, min_interval=float(cfg["min_interval_seconds"]), respect_robots=False
        )  # documented API, not crawling

    def call(self, endpoint: str, note: str = "", **params) -> dict:
        self.ledger.charge(endpoint, note)
        url = f"{self.base}/{endpoint}"
        resp = self.http.get(url, params={**params, "key": self._key})
        public_url = resp.url.replace(self._key, "<KEY>")
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if resp.status_code != 200:
            err = body.get("error", {}) if isinstance(body, dict) else {}
            reason = (err.get("errors") or [{}])[0].get("reason", "")
            log_download(
                SOURCE_ID,
                public_url,
                http_status=resp.status_code,
                outcome="api_error",
                notes=f"{reason}: {err.get('message', '')}"[:300],
            )
            raise YouTubeAPIError(resp.status_code, reason, err.get("message", resp.text[:200]))
        body["_request"] = {
            "endpoint": endpoint,
            "params": {k: v for k, v in params.items()},
            "retrieved_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        return body


def current_run() -> str:
    """Collection-run folder (YYYY-MM-DD). Quota limits spread a run over several days, so the run
    date is fixed via ``SRL_YT_RUN`` (set by scripts/youtube/run_youtube.py --run); default today."""
    from srl.acquisition.fetch import RETRIEVED_ON

    return os.environ.get("SRL_YT_RUN") or RETRIEVED_ON


def raw_root() -> Path:
    from srl.acquisition.fetch import raw_dir

    return raw_dir(SOURCE_ID, current_run())


def save_yt(rel: str, content: str | bytes, **kwargs) -> Path:
    """save_raw into the current collection run (write-once, logged)."""
    from srl.acquisition.fetch import save_raw

    return save_raw(SOURCE_ID, rel, content, retrieved_on=current_run(), **kwargs)
