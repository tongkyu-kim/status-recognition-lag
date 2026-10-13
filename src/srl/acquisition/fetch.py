"""Polite HTTP retrieval and write-once storage of raw files (see docs/decisions.md D015).

Rules enforced here:

- ``robots.txt`` is honoured for every host (a disallowed URL raises :class:`AccessBlocked`).
- Requests to the same host are spaced by at least ``min_interval`` seconds; 429/5xx responses
  are retried with exponential backoff, never hammered.
- Login pages, CAPTCHAs and API-key walls are not bypassed: callers record them as manual actions.
- :func:`save_raw` writes into ``data/raw/<source_id>/<retrieved_on>/`` and never overwrites. If a
  file already exists with identical content the write is a no-op; different content raises.
- Every attempt is appended to ``metadata/download_log.csv``.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import os
import threading
import time
import urllib.robotparser
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

from srl.utils.config import get_path
from srl.utils.paths import project_root, relpath

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; status-recognition-lag academic research; "
    "polite rate-limited retrieval of public data)"
)
# Retrieval folder date. Multi-day collections pin it (SRL_RETRIEVAL_DATE) so a resumed run continues
# in the original folder instead of starting an empty new one.
RETRIEVED_ON = os.environ.get("SRL_RETRIEVAL_DATE") or date.today().isoformat()
LOG_COLUMNS = [
    "timestamp",
    "source_id",
    "url",
    "method",
    "http_status",
    "dest",
    "bytes",
    "sha256",
    "outcome",
    "notes",
]
_log_lock = threading.Lock()
MAX_PATH = 259  # Windows limit without the LongPathsEnabled registry setting


class AccessBlocked(RuntimeError):
    """robots.txt disallows the URL, or the server requires login/key/CAPTCHA."""


class RawOverwriteError(FileExistsError):
    """A raw file already exists with different content."""


def metadata_dir() -> Path:
    path = project_root() / "metadata"
    path.mkdir(exist_ok=True)
    return path


def log_download(
    source_id: str,
    url: str,
    *,
    method: str = "GET",
    http_status: int | str = "",
    dest: Path | str = "",
    nbytes: int | str = "",
    sha256: str = "",
    outcome: str = "ok",
    notes: str = "",
) -> None:
    path = metadata_dir() / "download_log.csv"
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source_id": source_id,
        "url": url,
        "method": method,
        "http_status": http_status,
        "dest": relpath(dest) if dest else "",
        "bytes": nbytes,
        "sha256": sha256,
        "outcome": outcome,
        "notes": notes,
    }
    with _log_lock:
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=LOG_COLUMNS)
            if new:
                writer.writeheader()
            writer.writerow(row)


class PoliteSession:
    """``requests.Session`` wrapper with robots.txt checks, per-host spacing and backoff."""

    def __init__(
        self,
        source_id: str,
        *,
        min_interval: float = 1.0,
        timeout: float = 60,
        max_retries: int = 4,
        respect_robots: bool = True,
        headers: dict | None = None,
    ):
        self.source_id = source_id
        self.min_interval = min_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.respect_robots = respect_robots
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, **(headers or {})})
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _robots_ok(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parts = urlparse(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            parser = urllib.robotparser.RobotFileParser()
            try:
                resp = self.session.get(host + "/robots.txt", timeout=30)
                if resp.status_code == 200 and "text/plain" in resp.headers.get("Content-Type", ""):
                    parser.parse(resp.text.splitlines())
                    self._robots[host] = parser
                else:  # no robots.txt (or an HTML error page) -> no restrictions declared
                    self._robots[host] = None
            except requests.RequestException:
                self._robots[host] = None
        parser = self._robots[host]
        return True if parser is None else parser.can_fetch(USER_AGENT, url)

    def _wait(self, url: str) -> None:
        host = urlparse(url).netloc
        elapsed = time.monotonic() - self._last.get(host, 0.0)
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last[host] = time.monotonic()

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        if not self._robots_ok(url):
            log_download(self.source_id, url, method=method, outcome="robots_disallowed")
            raise AccessBlocked(f"robots.txt disallows {url}")
        kwargs.setdefault("timeout", self.timeout)
        delay = max(self.min_interval, 2.0)
        for attempt in range(self.max_retries + 1):
            self._wait(url)
            try:
                resp = self.session.request(method, url, **kwargs)
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    log_download(self.source_id, url, method=method, outcome="error", notes=str(exc)[:300])
                    raise
                logger.warning("%s %s failed (%s); retry in %.0fs", method, url, exc, delay)
                time.sleep(delay)
                delay *= 2
                continue
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                wait = float(resp.headers.get("Retry-After", delay) or delay)
                logger.warning("%s %s -> %s; retry in %.0fs", method, url, resp.status_code, wait)
                time.sleep(min(wait, 300))
                delay *= 2
                continue
            return resp
        return resp  # pragma: no cover

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self.request("POST", url, **kwargs)


def raw_dir(source_id: str, retrieved_on: str = RETRIEVED_ON) -> Path:
    path = get_path("data.raw") / source_id / retrieved_on
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_raw(
    source_id: str,
    relname: str,
    content: bytes | str,
    *,
    url: str = "",
    retrieved_on: str = RETRIEVED_ON,
    http_status: int | str = "",
    notes: str = "",
    log: bool = True,
) -> Path:
    """Write ``content`` to ``data/raw/<source_id>/<retrieved_on>/<relname>`` exactly once."""
    data = content.encode("utf-8") if isinstance(content, str) else content
    dest = raw_dir(source_id, retrieved_on) / relname
    if len(str(dest)) + 5 > MAX_PATH:
        raise OSError(
            f"Path too long for Windows MAX_PATH ({len(str(dest))} chars): {relpath(dest)}; "
            "use a shorter relname"
        )
    digest = hashlib.sha256(data).hexdigest()
    if dest.exists():
        existing = hashlib.sha256(dest.read_bytes()).hexdigest()
        if existing == digest:
            return dest
        raise RawOverwriteError(
            f"{relpath(dest)} exists with different content; raw files are "
            "immutable - use a new retrieval folder"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    if log:
        log_download(
            source_id, url, http_status=http_status, dest=dest, nbytes=len(data), sha256=digest, notes=notes
        )
    return dest


def raw_exists(source_id: str, relname: str, retrieved_on: str = RETRIEVED_ON) -> bool:
    return (get_path("data.raw") / source_id / retrieved_on / relname).exists()


def write_folder_readme(source_id: str, text: str, retrieved_on: str = RETRIEVED_ON) -> Path:
    """(Re)write the provenance README of a retrieval folder (README.md is not a data file)."""
    path = raw_dir(source_id, retrieved_on) / "README.md"
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path
