"""Pre-registered YouTube sampling frame (config/youtube_frame.yaml; docs/youtube_frame_protocol.md).

Design: fixed news-channel whitelist x standard Korean country name x identical event-relative
windows. One search cell = country x period x channel, searched with order=date and paginated to
exhaustion (date-cursor continuation past YouTube's ~500-result cap). Video selection never uses
comment content, volume, views or sentiment:

    search  -> video universe (every video returned, cached)
    videos  -> metadata (batched 50 ids / 1 unit)
    classify-> inclusion rules; exclusions and manual-review items recorded with reasons
    freeze  -> per country x period: census or seeded simple random sample (n <= ceiling);
               sorted sample ids hashed and time-stamped BEFORE any comment is downloaded
    comments-> all top-level comments of frozen videos only

Every API call is (1) budget-checked, (2) cached under data/raw/youtube_frame/<collection_id>/,
(3) logged in metadata/youtube_frame_ledger.csv. Cached responses are never re-requested.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from srl.acquisition.fetch import metadata_dir, raw_dir, save_raw
from srl.utils.config import get_path, load_config
from srl.utils.paths import project_root
from srl.youtube.api import (
    QuotaExhausted,
    QuotaLedger,
    YouTubeAPIError,
    YouTubeClient,
    hash_salt,
    minimize_comment_resource,
)
from srl.youtube.tables import hangul_share, iso_duration_seconds

logger = logging.getLogger(__name__)
SOURCE_ID = "youtube_frame"
KST = timezone(timedelta(hours=9))
LEDGER_COLUMNS = [
    "timestamp_utc",
    "quota_day_pt",
    "endpoint",
    "cell_id",
    "country",
    "period",
    "channel",
    "query",
    "page_token",
    "cursor_published_before",
    "page_no",
    "units",
    "items_returned",
    "status",
    "cache_file",
    "note",
]


# --------------------------------------------------------------------------- configuration
def cfg() -> dict:
    return load_config("youtube_frame")


def config_sha256() -> str:
    return hashlib.sha256((project_root() / "config" / "youtube_frame.yaml").read_bytes()).hexdigest()


def cache_root() -> Path:
    return raw_dir(SOURCE_ID, cfg()["collection_id"])


def out_dir() -> Path:
    path = get_path("data.processed") / "youtube_frame"
    path.mkdir(parents=True, exist_ok=True)
    return path


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


@dataclass(frozen=True)
class Cell:
    country: str
    period: str
    channel: str

    @property
    def cell_id(self) -> str:
        return f"{self.country}_{self.period}_{self.channel}"


def window(country: str, period: str) -> tuple[date, date]:
    """[start, end) in Korea-time calendar dates."""
    c = cfg()
    ev = date.fromisoformat(c["events"][country]["date"])
    m0 = date(ev.year, ev.month, 1)
    w = c["windows"][period]
    return add_months(m0, w["from_month"]), add_months(m0, w["to_month"] + 1)


def rfc3339_utc(d: date) -> str:
    """Midnight KST of ``d`` as an RFC 3339 UTC timestamp (the API's required format)."""
    return datetime(d.year, d.month, d.day, tzinfo=KST).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def channels() -> dict[str, dict]:
    return {ch["key"]: ch for ch in cfg()["channels"]}


def plan_cells() -> pd.DataFrame:
    c = cfg()
    rows = []
    for iso in c["events"]:
        for period in c["windows"]:
            start, end = window(iso, period)
            for key, ch in channels().items():
                created = date.fromisoformat(ch["created"])
                available = created < end
                rows.append(
                    {
                        "cell_id": Cell(iso, period, key).cell_id,
                        "country": iso,
                        "period": period,
                        "channel": key,
                        "window_start_kst": start.isoformat(),
                        "window_end_kst_exclusive": end.isoformat(),
                        "channel_created": ch["created"],
                        "channel_partial_window": available and created > start,
                        "plan_status": "search" if available else "channel_not_on_youtube",
                    }
                )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- ledger & budget
def ledger_path() -> Path:
    return metadata_dir() / "youtube_frame_ledger.csv"


def log_call(**row) -> None:
    path = ledger_path()
    new = not path.exists()
    row = {k: row.get(k, "") for k in LEDGER_COLUMNS}
    row["timestamp_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
    row["quota_day_pt"] = QuotaLedger.quota_day()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LEDGER_COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)


def read_ledger() -> pd.DataFrame:
    return (
        pd.read_csv(ledger_path(), dtype=str, keep_default_na=False)
        if ledger_path().exists()
        else pd.DataFrame(columns=LEDGER_COLUMNS)
    )


class Budget:
    """Frame-level quota policy on top of the shared daily quota ledger."""

    def __init__(self):
        q = cfg()["quota"]
        self.daily, self.reserve = int(q["daily_units"]), int(q["reserve_units"])
        self.max_search = int(q["max_search_requests_per_day"])
        self.min_cell = int(q["min_units_to_start_cell"])
        self.shared = QuotaLedger()

    def used(self) -> int:
        return self.shared.used_today()

    def remaining(self) -> int:
        return self.daily - self.reserve - self.used()

    def searches_today(self) -> int:
        led = read_ledger()
        day = QuotaLedger.quota_day()
        return int(
            ((led["endpoint"] == "search") & (led["quota_day_pt"] == day) & (led["status"] == "ok")).sum()
        )

    def can_search(self, starting_cell: bool) -> bool:
        need = self.min_cell if starting_cell else 100
        return self.searches_today() < self.max_search and self.remaining() >= need

    def can_spend(self, units: int) -> bool:
        return self.remaining() >= units


# --------------------------------------------------------------------------- search
def _cell_dir(cell_id: str) -> Path:
    return cache_root() / "search" / cell_id


def cell_pages(cell_id: str) -> list[dict]:
    d = _cell_dir(cell_id)
    return (
        [json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("p*.json"))] if d.exists() else []
    )


def cell_done(cell_id: str) -> dict | None:
    """Completion marker. v1 markers stay valid for census cells; v1 day-sample completions are
    superseded by protocol v2 (those cells continue as censuses)."""
    for name in ("_done_v2.json", "_done.json"):
        f = _cell_dir(cell_id) / name
        if f.exists():
            rec = json.loads(f.read_text(encoding="utf-8"))
            if name == "_done.json" and rec.get("status") == "complete_day_sample":
                continue
            return rec
    return None


def _mark_done(cell_id: str, status: str, pages: list[dict]) -> None:
    ids = {it["id"]["videoId"] for p in pages for it in p.get("items", []) if it.get("id", {}).get("videoId")}
    save_raw(
        SOURCE_ID,
        f"search/{cell_id}/_done_v2.json",
        json.dumps(
            {
                "cell_id": cell_id,
                "status": status,
                "pages": len(pages),
                "unique_videos": len(ids),
                "completed_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        ),
        retrieved_on=cfg()["collection_id"],
        log=False,
    )


def run_search_cell(client: YouTubeClient, budget: Budget, row: pd.Series) -> str:
    """Advance one cell; returns 'done' | 'budget' (stopped for quota) ."""
    c, s = cfg(), cfg()["search"]
    cid = row["cell_id"]
    if cell_done(cid):
        return "done"
    if cell_mode(cid):
        return run_day_sample(client, budget, row)
    ch = channels()[row["channel"]]
    query = c["countries"][row["country"]]["query"]
    after = rfc3339_utc(date.fromisoformat(row["window_start_kst"]))
    before = rfc3339_utc(date.fromisoformat(row["window_end_kst_exclusive"]))
    pages = cell_pages(cid)
    while True:
        seen = {
            it["id"]["videoId"] for p in pages for it in p.get("items", []) if it.get("id", {}).get("videoId")
        }
        token, cursor = None, None
        if pages:
            last = pages[-1]
            if last.get("nextPageToken"):
                token, cursor = last["nextPageToken"], last["_frame"].get("cursor")
            elif s.get("date_cursor_continuation") and len(last.get("items", [])) >= s["maxResults"]:
                times = [it["snippet"]["publishedAt"] for p in pages for it in p.get("items", [])]
                cursor = min(times)
                if cursor == last["_frame"].get("cursor") and not last["_frame"].get("token"):
                    _mark_done(cid, "complete_cursor_stalled", pages)
                    return "done"
            else:
                _mark_done(cid, "complete", pages)
                return "done"
            if len(pages) >= s["max_pages_per_cell"]:
                _mark_done(cid, "capped", pages)
                return "done"
        if not budget.can_search(starting_cell=not pages):
            return "budget"
        params = {
            "part": s["part"],
            "type": s["type"],
            "order": s["order"],
            "maxResults": s["maxResults"],
            "regionCode": s["regionCode"],
            "q": query,
            "channelId": ch["id"],
            "publishedAfter": after,
            "publishedBefore": cursor or before,
        }
        if token:
            params["pageToken"] = token
        page_no = len(pages) + 1
        try:
            body = client.call("search", note=cid, **params)
        except QuotaExhausted:
            return "budget"
        except YouTubeAPIError as exc:
            log_call(
                endpoint="search",
                cell_id=cid,
                country=row["country"],
                period=row["period"],
                channel=row["channel"],
                query=query,
                page_token=token or "",
                page_no=page_no,
                units=100,
                status=f"error:{exc.reason}",
                note=str(exc)[:200],
            )
            if exc.reason == "invalidPageToken" and pages:  # expired token -> fall back to date cursor
                pages[-1]["nextPageToken"] = None
                continue
            raise
        body["_frame"] = {
            "cell_id": cid,
            "page_no": page_no,
            "token": token,
            "cursor": cursor,
            "config_sha256": config_sha256(),
        }
        rel = f"search/{cid}/p{page_no:02d}.json"
        save_raw(
            SOURCE_ID,
            rel,
            json.dumps(body, ensure_ascii=False),
            retrieved_on=c["collection_id"],
            url="search.list",
            http_status=200,
            notes=cid,
            log=False,
        )
        new_ids = {
            it["id"]["videoId"] for it in body.get("items", []) if it.get("id", {}).get("videoId")
        } - seen
        log_call(
            endpoint="search",
            cell_id=cid,
            country=row["country"],
            period=row["period"],
            channel=row["channel"],
            query=query,
            page_token=token or "",
            cursor_published_before=cursor or "",
            page_no=page_no,
            units=100,
            items_returned=len(body.get("items", [])),
            status="ok",
            cache_file=rel,
            note=f"new={len(new_ids)} totalResults~{body.get('pageInfo', {}).get('totalResults')}",
        )
        pages.append(body)
        if cursor and not token and not new_ids:  # cursor page returned nothing new -> census exhausted
            _mark_done(cid, "complete", pages)
            return "done"
        dense = s.get("dense_cell_rule")
        total = int(body.get("pageInfo", {}).get("totalResults") or 0)
        thr = dense.get("total_results_threshold") if dense else None  # v2: null (totalResults unreliable)
        if dense and (
            (
                thr is not None
                and page_no == 1
                and not token
                and not cursor
                and total >= thr
                and body.get("nextPageToken")
            )
            or (page_no >= dense["max_census_pages"] and body.get("nextPageToken"))
        ):
            return run_day_sample(client, budget, row, reason=f"dense (page {page_no}, totalResults~{total})")


def sampled_days(row) -> list[date]:
    start = date.fromisoformat(row["window_start_kst"])
    end = date.fromisoformat(row["window_end_kst_exclusive"])
    days = [start + timedelta(days=i) for i in range((end - start).days)]
    k = int(cfg()["search"]["dense_cell_rule"]["days_per_cell"])
    seed = int(cfg()["sampling"]["seed"]) + int(hashlib.sha256(row["cell_id"].encode()).hexdigest()[:8], 16)
    idx = np.random.default_rng(seed).choice(len(days), size=min(k, len(days)), replace=False)
    return sorted(days[i] for i in idx)


def run_day_sample(client: YouTubeClient, budget: Budget, row, reason: str = "") -> str:
    """Day-cluster probability sample for a dense cell (resumable day by day)."""
    c, s = cfg(), cfg()["search"]
    cid = row["cell_id"]
    mode_file = _cell_dir(cid) / "_mode_v2.json"
    days = sampled_days(row)
    if not mode_file.exists():
        n_days = (
            date.fromisoformat(row["window_end_kst_exclusive"]) - date.fromisoformat(row["window_start_kst"])
        ).days
        save_raw(
            SOURCE_ID,
            f"search/{cid}/_mode_v2.json",
            json.dumps(
                {
                    "cell_id": cid,
                    "mode": "day_cluster_sample",
                    "reason": reason,
                    "days": [d.isoformat() for d in days],
                    "days_in_window": n_days,
                    "inclusion_probability": len(days) / n_days,
                    "switched_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                }
            ),
            retrieved_on=c["collection_id"],
            log=False,
        )
    ch = channels()[row["channel"]]
    query = c["countries"][row["country"]]["query"]
    for d in days:
        tag = d.strftime("%Y%m%d")
        dpages = sorted(_cell_dir(cid).glob(f"d{tag}_p*.json"))
        token = None
        if dpages:
            last = json.loads(dpages[-1].read_text(encoding="utf-8"))
            if not last.get("nextPageToken"):
                continue
            token = last["nextPageToken"]
        while True:
            if not budget.can_search(starting_cell=False):
                return "budget"
            params = {
                "part": s["part"],
                "type": s["type"],
                "order": s["order"],
                "maxResults": s["maxResults"],
                "regionCode": s["regionCode"],
                "q": query,
                "channelId": ch["id"],
                "publishedAfter": rfc3339_utc(d),
                "publishedBefore": rfc3339_utc(d + timedelta(days=1)),
            }
            if token:
                params["pageToken"] = token
            page_no = len(dpages) + 1
            try:
                body = client.call("search", note=f"{cid} day {tag}", **params)
            except QuotaExhausted:
                return "budget"
            body["_frame"] = {
                "cell_id": cid,
                "mode": "day",
                "day": d.isoformat(),
                "page_no": page_no,
                "token": token,
                "config_sha256": config_sha256(),
            }
            rel = f"search/{cid}/d{tag}_p{page_no:02d}.json"
            save_raw(
                SOURCE_ID,
                rel,
                json.dumps(body, ensure_ascii=False),
                retrieved_on=c["collection_id"],
                url="search.list",
                http_status=200,
                notes=f"{cid} {tag}",
                log=False,
            )
            log_call(
                endpoint="search",
                cell_id=cid,
                country=row["country"],
                period=row["period"],
                channel=row["channel"],
                query=query,
                page_token=token or "",
                page_no=page_no,
                units=100,
                items_returned=len(body.get("items", [])),
                status="ok",
                cache_file=rel,
                note=f"day_sample {tag} totalResults~{body.get('pageInfo', {}).get('totalResults')}",
            )
            dpages.append(Path(rel))
            token = body.get("nextPageToken")
            if not token:
                break
    _mark_done(
        cid,
        "complete_day_sample",
        cell_pages(cid)
        + [json.loads(f.read_text(encoding="utf-8")) for f in sorted(_cell_dir(cid).glob("d*_p*.json"))],
    )
    return "done"


def cell_mode(cell_id: str) -> dict | None:
    """Day-sample marker (v2 only; v1 `_mode.json` switches are superseded)."""
    f = _cell_dir(cell_id) / "_mode_v2.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


# --------------------------------------------------------------------------- metadata
def universe_ids() -> list[str]:
    ids = []
    for d in sorted((cache_root() / "search").glob("*")) if (cache_root() / "search").exists() else []:
        for f in sorted(d.glob("*_p*.json")) + sorted(d.glob("p*.json")):
            ids += [
                it["id"]["videoId"]
                for it in json.loads(f.read_text(encoding="utf-8")).get("items", [])
                if it.get("id", {}).get("videoId")
            ]
    return list(dict.fromkeys(ids))


def cached_video_items() -> dict[str, dict]:
    out, requested = {}, set()
    for f in sorted((cache_root() / "videos").glob("*.json")) if (cache_root() / "videos").exists() else []:
        body = json.loads(f.read_text(encoding="utf-8"))
        requested.update(body.get("_requested", []))
        out.update({it["id"]: it for it in body.get("items", [])})
    out["__requested__"] = requested  # type: ignore[assignment]
    return out


def fetch_metadata(client: YouTubeClient, budget: Budget) -> int:
    cached = cached_video_items()
    todo = [v for v in universe_ids() if v not in cached["__requested__"]]
    n = 0
    for k in range(0, len(todo), 50):
        if not budget.can_spend(1):
            break
        batch = todo[k : k + 50]
        body = client.call(
            "videos",
            note=f"{len(batch)} ids",
            part="snippet,contentDetails,statistics,status",
            id=",".join(batch),
            maxResults=50,
        )
        body["_requested"] = batch
        rel = f"videos/b_{hashlib.sha1(','.join(batch).encode()).hexdigest()[:12]}.json"
        save_raw(
            SOURCE_ID,
            rel,
            json.dumps(body, ensure_ascii=False),
            retrieved_on=cfg()["collection_id"],
            url="videos.list",
            http_status=200,
            log=False,
        )
        log_call(
            endpoint="videos",
            units=1,
            items_returned=len(body.get("items", [])),
            status="ok",
            cache_file=rel,
            note=f"requested={len(batch)}",
        )
        n += 1
    return n


# --------------------------------------------------------------------------- classification
def _in_text(forms: list[str], text: str) -> bool:
    return any(f and f in text for f in forms)


def classify(v: dict | None, row: dict) -> tuple[str, str]:
    """Return (status, reason). status in {included, excluded, manual_review, pending_metadata}."""
    c = cfg()
    inc = c["inclusion"]
    if v is None:
        return "pending_metadata", "videos.list not yet retrieved"
    if v == "missing":
        return "excluded", "unavailable_at_metadata_retrieval (deleted/private)"
    sn, cd = v["snippet"], v.get("contentDetails", {})
    if sn.get("channelId") not in {ch["id"] for ch in c["channels"]}:
        return "excluded", "channel_not_in_whitelist"
    pub = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")).astimezone(KST).date()
    if not (
        date.fromisoformat(row["window_start_kst"])
        <= pub
        < date.fromisoformat(row["window_end_kst_exclusive"])
    ):
        return "excluded", "outside_window"
    lang = (sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "").lower()
    share = hangul_share(sn.get("title", ""))
    if not (
        lang.startswith("ko")
        or (share == share and share >= inc["korean_language"]["hangul_share_title_min"])
    ):
        return "excluded", f"not_korean_language (lang={lang or 'NA'}, hangul_share_title={share:.2f})"
    fmt = inc["format"]
    if fmt["exclude_live_or_upcoming"] and sn.get("liveBroadcastContent") in ("live", "upcoming"):
        return "excluded", "live_or_upcoming"
    dur = iso_duration_seconds(cd.get("duration"))
    text_all = f"{sn.get('title', '')} {sn.get('description', '')} {' '.join(sn.get('tags', []))}"
    if dur == dur and dur < fmt["min_duration_s"] or re.search(r"#shorts?\b", text_all, re.I):
        return "excluded", f"short_form (duration_s={dur})"
    if dur == dur and dur > fmt["max_duration_s"]:
        return "excluded", f"full_programme_or_stream_replay (duration_s={dur})"
    country = c["countries"][row["country"]]
    title = sn.get("title", "")
    sub = inc.get("substantive", {})
    if _in_text(country["title_include"], title):
        return "included", "country_in_title"
    review_forms = country.get("title_review", [])
    if sub.get("hanja_token_include") and any(
        re.search(rf"(?<![가-힣A-Za-z0-9]){re.escape(f)}", title) for f in review_forms
    ):
        return "included", "country_hanja_form_in_title (v3: not glued to preceding character)"
    if _in_text(review_forms, title):
        return "manual_review", "ambiguous_country_form_in_title"
    in_desc = _in_text(country["title_include"], sn.get("description", ""))
    in_tags = _in_text(country["title_include"], " ".join(sn.get("tags", [])))
    if in_desc:
        return "manual_review", "country_in_description_only" if sub.get("tags_only") else (
            "country_in_description_or_tags_only"
        )
    if in_tags:
        if sub.get("tags_only") == "exclude":
            return "excluded", "country_in_tags_only (incidental; protocol v3)"
        return "manual_review", "country_in_description_or_tags_only"
    return "excluded", "country_absent_from_title_description_tags (incidental match)"


def review_decisions() -> pd.DataFrame:
    files = sorted((get_path("data.raw") / "human_coding").glob("*/youtube_frame_review*.csv"))
    if not files:
        return pd.DataFrame(columns=["video_id", "country", "decision"])
    df = pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)
    return df.drop_duplicates(["video_id", "country"], keep="last")


def build_universe() -> pd.DataFrame:
    plan = plan_cells().set_index("cell_id")
    meta = cached_video_items()
    requested = meta.pop("__requested__")
    rows = []
    for d in sorted((cache_root() / "search").glob("*")) if (cache_root() / "search").exists() else []:
        cid = d.name
        p = plan.loc[cid]
        mode = cell_mode(cid)
        v1_day_files = sorted(d.glob("d*_p*.json")) if mode is None else []
        day_files = [] if mode is None else sorted(d.glob("d*_p*.json"))
        census_ids = {
            it["id"]["videoId"]
            for f in sorted(d.glob("p*.json"))
            for it in json.loads(f.read_text(encoding="utf-8")).get("items", [])
            if it.get("id", {}).get("videoId")
        }
        for f in v1_day_files:  # superseded v1 day-sample pages: keep as audit rows only
            for it in json.loads(f.read_text(encoding="utf-8")).get("items", []):
                vid = it.get("id", {}).get("videoId")
                if vid and vid not in census_ids:
                    rows.append(
                        {
                            "cell_id": cid,
                            "country": p["country"],
                            "period": p["period"],
                            "channel": p["channel"],
                            "cell_mode": "census",
                            "p_cell": 1.0,
                            "video_id": vid,
                            "search_page": f.stem,
                            "rank_in_page": None,
                            "published_at": it["snippet"].get("publishedAt"),
                            "channel_id": it["snippet"].get("channelId"),
                            "title": it["snippet"].get("title"),
                            "status": "excluded",
                            "reason": "superseded_v1_day_sample_page (not yet reached by census)",
                            "duration_s": np.nan,
                            "comment_count": np.nan,
                        }
                    )
        day_ids = {
            it["id"]["videoId"]
            for f in day_files
            for it in json.loads(f.read_text(encoding="utf-8")).get("items", [])
            if it.get("id", {}).get("videoId")
        }
        p_cell = mode["inclusion_probability"] if mode else 1.0
        for f in day_files + sorted(d.glob("p*.json")):
            probe = mode is not None and f.name.startswith("p")
            body = json.loads(f.read_text(encoding="utf-8"))
            for rank, it in enumerate(body.get("items", []), start=1):
                vid = it.get("id", {}).get("videoId")
                if not vid or (probe and vid in day_ids):
                    continue
                v = meta.get(vid) or ("missing" if vid in requested else None)
                status, reason = classify(v, {**p.to_dict(), "country": p["country"]})
                if probe:
                    status, reason = "excluded", "dense_cell_probe_not_in_probability_sample"
                sn = v["snippet"] if isinstance(v, dict) else it["snippet"]
                rows.append(
                    {
                        "cell_id": cid,
                        "country": p["country"],
                        "period": p["period"],
                        "channel": p["channel"],
                        "cell_mode": mode["mode"] if mode else "census",
                        "p_cell": p_cell,
                        "video_id": vid,
                        "search_page": f.stem,
                        "rank_in_page": rank,
                        "published_at": sn.get("publishedAt"),
                        "channel_id": sn.get("channelId"),
                        "title": sn.get("title"),
                        "status": status,
                        "reason": reason,
                        "duration_s": iso_duration_seconds(v.get("contentDetails", {}).get("duration"))
                        if isinstance(v, dict)
                        else np.nan,
                        "comment_count": pd.to_numeric(
                            v.get("statistics", {}).get("commentCount"), errors="coerce"
                        )
                        if isinstance(v, dict)
                        else np.nan,
                    }
                )
    uni = pd.DataFrame(rows).drop_duplicates(["cell_id", "video_id"])
    if uni.empty:
        return uni
    dec = review_decisions()
    if not dec.empty:
        uni = uni.merge(dec[["video_id", "country", "decision"]], on=["video_id", "country"], how="left")
        m = (uni["status"] == "manual_review") & uni["decision"].isin(["include", "exclude"])
        uni.loc[m, "reason"] = uni.loc[m, "reason"] + " -> manual:" + uni.loc[m, "decision"]
        uni.loc[m, "status"] = uni.loc[m, "decision"].map({"include": "included", "exclude": "excluded"})
        uni = uni.drop(columns="decision")
    return uni


# --------------------------------------------------------------------------- freeze & sample
def freeze_dir() -> Path:
    path = get_path("data.interim") / "youtube_frame" / "frozen"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cell_seed(country: str, period: str) -> int:
    h = int(hashlib.sha256(f"{country}|{period}".encode()).hexdigest()[:8], 16)
    return int(cfg()["sampling"]["seed"]) + h


def freeze_ready(uni: pd.DataFrame, plan: pd.DataFrame, country: str, period: str) -> tuple[bool, str]:
    cells = plan[
        (plan["country"] == country) & (plan["period"] == period) & (plan["plan_status"] == "search")
    ]
    not_done = [c for c in cells["cell_id"] if not cell_done(c)]
    if not_done:
        return False, f"search incomplete: {len(not_done)} channel cells"
    u = uni[(uni["country"] == country) & (uni["period"] == period)] if not uni.empty else uni
    if not u.empty and (u["status"] == "pending_metadata").any():
        return False, "metadata pending"
    if not u.empty and (u["status"] == "manual_review").any():
        return False, f"{int((u['status'] == 'manual_review').sum())} videos await manual review"
    return True, ""


def freeze(uni: pd.DataFrame) -> list[str]:
    """Freeze every ready country x period that is not frozen yet. Returns frozen keys."""
    plan, done = plan_cells(), []
    n_max = int(cfg()["sampling"]["max_videos_per_country_period"])
    log = metadata_dir() / "youtube_frame_freeze_log.csv"
    for (country, period), _ in plan.groupby(["country", "period"]):
        f = freeze_dir() / f"{country}_{period}.json"
        if f.exists():
            continue
        ok, why = freeze_ready(uni, plan, country, period)
        if not ok:
            continue
        u = uni[(uni["country"] == country) & (uni["period"] == period)] if not uni.empty else uni
        included = sorted(set(u.loc[u["status"] == "included", "video_id"])) if not u.empty else []
        N = len(included)
        if N <= n_max:
            sampled, prob, method = included, 1.0 if N else np.nan, "census"
        else:
            rng = np.random.default_rng(_cell_seed(country, period))
            sampled = sorted(rng.choice(included, size=n_max, replace=False).tolist())
            prob, method = n_max / N, "simple_random_sample"
        digest = hashlib.sha256("\n".join(sampled).encode()).hexdigest()
        rec = {
            "country": country,
            "period": period,
            "protocol_version": cfg()["protocol_version"],
            "config_sha256": config_sha256(),
            "method": method,
            "N_included": N,
            "n_sampled": len(sampled),
            "sampling_probability": prob,
            "seed": _cell_seed(country, period),
            "included_ids": included,
            "sampled_ids": sampled,
            "sampled_ids_sha256": digest,
            "frozen_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "comments_downloaded_before_freeze": False,
        }
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        new = not log.exists()
        with log.open("a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(
                    [
                        "frozen_utc",
                        "country",
                        "period",
                        "method",
                        "N_included",
                        "n_sampled",
                        "sampling_probability",
                        "sampled_ids_sha256",
                        "config_sha256",
                        "protocol_version",
                    ]
                )
            w.writerow(
                [
                    rec["frozen_utc"],
                    country,
                    period,
                    method,
                    N,
                    len(sampled),
                    prob,
                    digest,
                    rec["config_sha256"],
                    rec["protocol_version"],
                ]
            )
        done.append(f"{country}_{period}")
    return done


def frozen_samples() -> dict[str, dict]:
    out = {}
    for f in sorted(freeze_dir().glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if hashlib.sha256("\n".join(rec["sampled_ids"]).encode()).hexdigest() != rec["sampled_ids_sha256"]:
            raise RuntimeError(f"Frozen sample {f.name} fails its hash check - it was modified.")
        out[f.stem] = rec
    return out


# --------------------------------------------------------------------------- comments
def _vid_done(video_id: str) -> dict | None:
    f = cache_root() / "comments" / video_id / "_done.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def fetch_comments(client: YouTubeClient, budget: Budget, uni: pd.DataFrame) -> int:
    c = cfg()["comments"]
    salt = hash_salt()
    counts = uni.drop_duplicates("video_id").set_index("video_id")["comment_count"] if not uni.empty else {}
    n_videos = 0
    for key, rec in frozen_samples().items():
        for vid in rec["sampled_ids"]:
            if _vid_done(vid):
                continue
            expected = max(1, math.ceil(float(counts.get(vid, 0) or 0) / c["maxResults"]))
            vdir = cache_root() / "comments" / vid
            pages = sorted(vdir.glob("p*.json")) if vdir.exists() else []
            if not pages and not budget.can_spend(expected):
                logger.info(
                    "Stopping comments: %s needs ~%d units, %d left", vid, expected, budget.remaining()
                )
                return n_videos
            token = json.loads(pages[-1].read_text(encoding="utf-8")).get("nextPageToken") if pages else None
            if pages and not token:
                _finish_video(vid, "complete", len(pages))
                continue
            page_no = len(pages)
            status = "complete"
            while True:
                if not budget.can_spend(1):
                    return n_videos
                params = {
                    "part": "snippet",
                    "videoId": vid,
                    "maxResults": c["maxResults"],
                    "order": c["order"],
                    "textFormat": c["textFormat"],
                }
                if token:
                    params["pageToken"] = token
                try:
                    body = client.call("commentThreads", note=vid, **params)
                except YouTubeAPIError as exc:
                    status = exc.reason or f"http_{exc.status}"
                    log_call(
                        endpoint="commentThreads", cell_id=key, units=1, status=f"error:{status}", note=vid
                    )
                    break
                page_no += 1
                body["items"] = [minimize_comment_resource(it, salt) for it in body.get("items", [])]
                rel = f"comments/{vid}/p{page_no:03d}.json"
                save_raw(
                    SOURCE_ID,
                    rel,
                    json.dumps(body, ensure_ascii=False),
                    retrieved_on=cfg()["collection_id"],
                    url="commentThreads.list",
                    http_status=200,
                    log=False,
                )
                log_call(
                    endpoint="commentThreads",
                    cell_id=key,
                    units=1,
                    items_returned=len(body.get("items", [])),
                    page_token=token or "",
                    page_no=page_no,
                    status="ok",
                    cache_file=rel,
                    note=vid,
                )
                token = body.get("nextPageToken")
                if not token:
                    break
            _finish_video(vid, status, page_no)
            n_videos += 1
    return n_videos


def _finish_video(vid: str, status: str, pages: int) -> None:
    save_raw(
        SOURCE_ID,
        f"comments/{vid}/_done.json",
        json.dumps(
            {
                "video_id": vid,
                "status": status,
                "pages": pages,
                "completed_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        ),
        retrieved_on=cfg()["collection_id"],
        log=False,
    )


def comments_table() -> pd.DataFrame:
    rows = []
    root = cache_root() / "comments"
    for vdir in sorted(root.glob("*")) if root.exists() else []:
        for f in sorted(vdir.glob("p*.json")):
            for th in json.loads(f.read_text(encoding="utf-8")).get("items", []):
                top = th["snippet"]["topLevelComment"]
                sn = top["snippet"]
                rows.append(
                    {
                        "comment_id": top["id"],
                        "video_id": vdir.name,
                        "channel_id": sn.get("channelId"),
                        "parent_id": None,
                        "published_at": sn.get("publishedAt"),
                        "updated_at": sn.get("updatedAt"),
                        "text": sn.get("textOriginal") or sn.get("textDisplay"),
                        "like_count": sn.get("likeCount"),
                        "reply_count": th["snippet"].get("totalReplyCount"),
                        "author_hash": sn.get("authorHash"),
                    }
                )
    return pd.DataFrame(rows).drop_duplicates("comment_id") if rows else pd.DataFrame()


# --------------------------------------------------------------------------- status & outputs
def collection_status(uni: pd.DataFrame) -> pd.DataFrame:
    plan = plan_cells()
    frozen = frozen_samples()
    rows = []
    for r in plan.itertuples():
        pages, done = cell_pages(r.cell_id), cell_done(r.cell_id)
        u = uni[uni["cell_id"] == r.cell_id] if not uni.empty else uni
        status = (
            r.plan_status
            if r.plan_status != "search"
            else (done["status"] if done else ("in_progress" if pages else "pending"))
        )
        rows.append(
            {
                **r._asdict(),
                "search_status": status,
                "search_pages": len(pages),
                "videos_returned": int(u["video_id"].nunique()) if not u.empty else 0,
                "included": int((u["status"] == "included").sum()) if not u.empty else 0,
                "manual_review": int((u["status"] == "manual_review").sum()) if not u.empty else 0,
                "excluded": int((u["status"] == "excluded").sum()) if not u.empty else 0,
                "country_period_frozen": f"{r.country}_{r.period}" in frozen,
            }
        )
    return pd.DataFrame(rows).drop(columns="Index")
