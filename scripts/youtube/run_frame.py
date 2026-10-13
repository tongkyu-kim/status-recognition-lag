"""Pre-registered YouTube sampling frame: plan, collect, build, status.

    python scripts/youtube/run_frame.py plan      # cells, quota estimate (no API calls)
    python scripts/youtube/run_frame.py collect   # one day's collection within the quota policy
    python scripts/youtube/run_frame.py build     # audit outputs + README (no API calls)
    python scripts/youtube/run_frame.py status    # end-of-day summary (no API calls)

Collection order each day: search cells (country x period x channel, in config order, finishing
cells before starting new ones) -> videos.list for new ids -> classification -> freeze ready
country x period samples -> comments for frozen samples. Rerunning never repeats a cached call.
Protocol: config/youtube_frame.yaml; docs/youtube_frame_protocol.md.
"""

import argparse
import math

import _bootstrap  # noqa: F401
import pandas as pd

from srl.utils.cli import run_step
from srl.utils.io import write_table
from srl.youtube import frame

# Prior pages-per-cell for estimation only (replaced by observed totalResults as cells are searched).
PRIOR_PAGES = {"CHN": 12, "VNM": 3, "IDN": 3, "THA": 2, "MMR": 2, "KHM": 2, "LAO": 1}


def estimate(uni: pd.DataFrame) -> dict:
    plan = frame.plan_cells()
    todo = plan[plan["plan_status"] == "search"]
    # pageInfo.totalResults is unreliable for filtered queries (D024), so estimates use observed page
    # counts and priors only. A cell costs at most max_census_pages + days_per_cell requests (v2 rule).
    dense = frame.cfg()["search"]["dense_cell_rule"]
    cap = int(dense["max_census_pages"]) + int(dense["days_per_cell"])
    pages_left, per_country = 0, {}
    for r in todo.itertuples():
        done = frame.cell_done(r.cell_id)
        got = len(frame.cell_pages(r.cell_id))
        full_last = got and len(frame.cell_pages(r.cell_id)[-1].get("items", [])) >= 50
        nxt = got + (1 if (full_last or not got) else 0)
        exp = got if done else min(cap, max(nxt, PRIOR_PAGES[r.country]))
        pages_left += 0 if done else max(exp - got, 0)
        per_country[r.country] = per_country.get(r.country, 0) + exp
    total_pages = sum(per_country.values())
    videos_est = total_pages * 50
    return {
        "search_cells": len(todo),
        "cells_channel_not_on_youtube": int((plan["plan_status"] != "search").sum()),
        "search_requests_expected_total": total_pages,
        "search_requests_remaining": pages_left,
        "search_units_remaining": pages_left * 100,
        "videos_list_units": math.ceil(videos_est / 50),
        "per_country_search_requests": per_country,
    }


def comment_units_estimate(uni: pd.DataFrame) -> int:
    fr = frame.frozen_samples()
    if not fr or uni.empty:
        return 0
    cc = uni.drop_duplicates("video_id").set_index("video_id")["comment_count"].fillna(0)
    return int(
        sum(
            max(1, math.ceil(cc.get(v, 0) / 100))
            for rec in fr.values()
            for v in rec["sampled_ids"]
            if not frame._vid_done(v)
        )
    )


def summary(logger, uni: pd.DataFrame, n_search_before: int) -> None:
    b = frame.Budget()
    st = frame.collection_status(uni)
    est = estimate(uni)
    com = frame.comments_table()
    searches_today = b.searches_today()
    srch = st[st["plan_status"] == "search"]
    done_cells = srch["search_status"].str.startswith(("complete", "capped")).sum()
    days = est["search_requests_remaining"] / max(1, b.max_search)
    cu = comment_units_estimate(uni)
    logger.info(
        "\n=== DAILY SUMMARY (quota day %s, US Pacific) ===\n"
        "quota used today: %d units | remaining before reserve: %d\n"
        "search requests today: %d (this run: %d) of max %d\n"
        "videos discovered (universe, unique): %d | retained (included): %d | "
        "manual review: %d | excluded: %d\n"
        "comments collected (total): %d\n"
        "search cells complete: %d / %d | pending or in progress: %d | channel not on YouTube: %d\n"
        "frozen country x period samples: %d / %d\n"
        "estimated remaining: %d search requests (~%.1f days at %d/day) + "
        "~%d comment units for frozen samples",
        frame.QuotaLedger.quota_day(),
        b.used(),
        b.remaining(),
        searches_today,
        searches_today - n_search_before,
        b.max_search,
        uni["video_id"].nunique() if not uni.empty else 0,
        uni.loc[uni["status"] == "included", "video_id"].nunique() if not uni.empty else 0,
        int((uni["status"] == "manual_review").sum()) if not uni.empty else 0,
        int((uni["status"] == "excluded").sum()) if not uni.empty else 0,
        len(com),
        done_cells,
        len(srch),
        len(srch) - done_cells,
        est["cells_channel_not_on_youtube"],
        len(frame.frozen_samples()),
        st.groupby(["country", "period"]).ngroups,
        est["search_requests_remaining"],
        days,
        b.max_search,
        cu,
    )


def build(logger) -> pd.DataFrame:
    out = frame.out_dir()
    uni = frame.build_universe()
    led = frame.read_ledger()
    q = led[led["endpoint"] == "search"] if not led.empty else led
    write_table(q, out / "youtube_queries.csv")
    if not uni.empty:
        write_table(uni, out / "video_universe.csv")
        write_table(uni[uni["status"] == "excluded"], out / "video_exclusions.csv")
        write_table(uni[uni["status"] == "manual_review"], out / "video_manual_review.csv")
        frozen = frame.frozen_samples()
        inc = uni[uni["status"] == "included"].copy()
        inc["country_period"] = inc["country"] + "_" + inc["period"]
        inc["frozen"] = inc["country_period"].isin(frozen)
        inc["sampled"] = [
            v in frozen.get(k, {}).get("sampled_ids", [])
            for k, v in zip(inc["country_period"], inc["video_id"], strict=True)
        ]
        inc["sampling_probability"] = inc["country_period"].map(
            {k: r["sampling_probability"] for k, r in frozen.items()}
        )
        inc["frozen_sha256"] = inc["country_period"].map(
            {k: r["sampled_ids_sha256"] for k, r in frozen.items()}
        )
        write_table(inc, out / "video_sample.csv")
    com = frame.comments_table()
    if not com.empty:
        write_table(com, out / "comments_raw.parquet")
    if not led.empty:
        led["units"] = pd.to_numeric(led["units"], errors="coerce").fillna(0)
        write_table(
            led.groupby(["quota_day_pt", "endpoint"])
            .agg(requests=("units", "size"), units=("units", "sum"))
            .reset_index(),
            out / "quota_log.csv",
        )
    write_table(frame.collection_status(uni), out / "collection_status.csv")
    write_readme(out, uni, led)
    return uni


def write_readme(out, uni, led) -> None:
    c = frame.cfg()
    ch = "\n".join(
        f"| {x['key']} | {x['name']} | `{x['id']}` | {x['type']} | {x['created']} |" for x in c["channels"]
    )
    co = "\n".join(
        f"| {k} | {v['name']} | {v['query']} | {', '.join(v['title_include'])} | "
        f"{', '.join(v.get('title_review', [])) or '-'} | "
        f"{c['events'][k]['date']} ({c['events'][k]['change']}) |"
        for k, v in c["countries"].items()
    )
    win = "\n".join(f"| {k} | {v['from_month']} .. {v['to_month']} |" for k, v in c["windows"].items())
    cells = frame.plan_cells()
    wtab = cells.drop_duplicates(["country", "period"])[
        ["country", "period", "window_start_kst", "window_end_kst_exclusive"]
    ]
    wt = "\n".join(
        f"| {r.country} | {r.period} | {r.window_start_kst} | {r.window_end_kst_exclusive} |"
        for r in wtab.itertuples()
    )
    unavailable = (
        cells[cells["plan_status"] != "search"]
        .groupby(["country", "period"])["channel"]
        .apply(lambda s: ", ".join(s))
        .reset_index()
    )
    un = (
        "\n".join(f"| {r.country} | {r.period} | {r.channel} |" for r in unavailable.itertuples())
        or "| - | - | - |"
    )
    dates = sorted(led["quota_day_pt"].unique()) if not led.empty else []
    nmax, seed = c["sampling"]["max_videos_per_country_period"], c["sampling"]["seed"]
    qmax, qmin = c["quota"]["max_search_requests_per_day"], c["quota"]["min_units_to_start_cell"]
    text = f"""# YouTube sampling frame v{c["protocol_version"]} - collection outputs

Generated by `scripts/youtube/run_frame.py build`. Protocol fixed on {c["fixed_on"]} in
`config/youtube_frame.yaml` (SHA-256 `{frame.config_sha256()}`); rationale in
`docs/youtube_frame_protocol.md`. Collection days (US Pacific quota days): {", ".join(dates) or "none yet"}.

## Sampling protocol
1. Sampling frame = fixed whitelist of Korean national news channels x standardized Korean country
   name x identical event-relative windows. No video is chosen by title, popularity, sentiment or
   comment activity.
2. One search cell = country x period x channel: `search.list` with `q=<country name>`,
   `channelId`, `type=video`, `order=date`, `maxResults=50`, fixed `publishedAfter/Before`,
   paginated to exhaustion; past YouTube's ~500-result cap the same query continues with a
   date cursor (`publishedBefore` = oldest result so far). Every executed query: `youtube_queries.csv`.
3. Every returned video enters `video_universe.csv` before any rule is applied.
4. Inclusion rules (in order): whitelist channel; inside window (KST); Korean language (audio/default
   language `ko*` or >= 50% Hangul title letters); format (61 s <= duration <= 60 min, not Shorts,
   not live/upcoming); substantive: country form in title -> included; ambiguous title form or
   country only in description/tags -> manual review; country absent from title, description and
   tags -> excluded. Exclusions with reasons: `video_exclusions.csv`; review queue:
   `video_manual_review.csv` (decisions go to `data/raw/human_coding/<date>/youtube_frame_review*.csv`,
   columns video_id,country,decision[include|exclude],reason,reviewer).
5. Sampling per country x period (pooled over channels): census if N <= {nmax},
   else simple random sample of {nmax} (seed {seed} + hash of
   country|period); probability n/N in `video_sample.csv`.
6. Freeze: a country x period is frozen only when all its channel cells are searched, metadata is
   complete and no review is pending. The sorted sampled ids are SHA-256 hashed and time-stamped in
   `data/interim/youtube_frame/frozen/` and `metadata/youtube_frame_freeze_log.csv` (git-tracked).
   Comments are downloaded ONLY for frozen samples, so selection is independent of comments.
7. Comments: all top-level comments (`commentThreads.list`, order=time, plain text); replies are
   not fetched (reply_count kept). Commenter identities are dropped/hashed at ingest (D017).

## Channel whitelist (criterion: all national terrestrial, 24-hour news and general-programming news channels)
| key | channel | id | type | YouTube channel created |
|---|---|---|---|---|
{ch}

## Country-name dictionary and events
| ISO3 | country | search term | title forms (include) | title forms (review) | event (WB upgrade) |
|---|---|---|---|---|---|
{co}

## Observation windows (months relative to the event month; month 0 excluded)
| period | months |
|---|---|
{win}

| country | period | start (KST) | end (exclusive) |
|---|---|---|---|
{wt}

Cells not searched because the channel was not yet on YouTube at the window end:
| country | period | channels |
|---|---|---|
{un}

## Quota strategy
Daily quota {c["quota"]["daily_units"]} units; reserve {c["quota"]["reserve_units"]}; at most
{qmax} search requests/day; a new cell starts only with >= {qmin}
units left; cells finish before new ones start (config order). All responses are cached; the
ledger `metadata/youtube_frame_ledger.csv` records every call (date, endpoint, cell, query, page
token, cursor, units, items, status). Daily totals: `quota_log.csv`.

## Known limitations
- YouTube search is an index, not an archive: recall of `search.list` is not guaranteed complete,
  and deleted/private videos are absent. The frame is a census of search-retrievable videos.
- Channel coverage differs by period: 2010-11 events (VNM, CHN, LAO, THA) fall largely before
  YTN (2013-05), KBS News (2013-08), SBS News (2014-05) and Yonhap News TV (2015-01) opened YouTube
  channels; early windows rely on MBC, MBN, JTBC, TV Chosun, Channel A. Windows are NOT shifted to
  favourable periods; coverage is reported per cell in `collection_status.csv`.
- Comments reflect the state at retrieval (edits/deletions since upload unknown); old videos may
  have had comments disabled or removed.
- IDN's post-event window contains a reversal (down-classified 2021-07).
- Title-based relevance may miss videos that discuss a country without naming it in the title;
  those with the name in description/tags are sent to manual review, not dropped.
- The day-1 exploratory pilot (data/raw/youtube/2026-09-30/) used relevance-ranked topical queries
  and is NOT part of this frame.
"""
    (out / "README.md").write_text(text, encoding="utf-8")


def check_completion(logger, uni: pd.DataFrame, task_name: str | None) -> bool:
    """Write NEXT_ACTION.txt; when everything is collected, write COLLECTION_COMPLETE.txt and
    disable the scheduled task (if a name was given)."""
    import subprocess
    from datetime import datetime

    out = frame.out_dir()
    st = frame.collection_status(uni)
    srch = st[st["plan_status"] == "search"]
    open_cells = int((~srch["search_status"].str.startswith(("complete", "capped"))).sum())
    groups = st.groupby(["country", "period"]).ngroups
    frozen = frame.frozen_samples()
    pending_meta = int((uni["status"] == "pending_metadata").sum()) if not uni.empty else 0
    review = uni[uni["status"] == "manual_review"] if not uni.empty else uni
    comments_left = [v for r in frozen.values() for v in r["sampled_ids"] if not frame._vid_done(v)]
    done = open_cells == 0 and pending_meta == 0 and len(frozen) == groups and not comments_left
    stamp = datetime.now().isoformat(timespec="seconds")
    lines = [
        f"Status at {stamp} (Korea time)",
        f"search cells still open: {open_cells}",
        f"videos awaiting metadata: {pending_meta}",
        f"frozen country x period samples: {len(frozen)} / {groups}",
        f"sampled videos still needing comments: {len(comments_left)}",
    ]
    if len(review):
        by = review.groupby(["country", "period"]).size()
        lines += [
            "",
            f"WAITING ON YOU: {len(review)} videos need manual review "
            "(data/processed/youtube_frame/video_manual_review.csv).",
            "Put decisions in data/raw/human_coding/<YYYY-MM-DD>/youtube_frame_review.csv",
            "with columns video_id,country,decision,reason,reviewer (decision = include | exclude).",
            "By country x period: " + ", ".join(f"{c}_{p}={n}" for (c, p), n in by.items()),
        ]
    (out / "NEXT_ACTION.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (out / "daily_summary.log").open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n\n")
    if done:
        (out / "COLLECTION_COMPLETE.txt").write_text(
            f"Frame collection complete at {stamp}\n", encoding="utf-8"
        )
        logger.info("FRAME COLLECTION COMPLETE")
        if task_name:
            r = subprocess.run(
                ["schtasks", "/Change", "/TN", task_name, "/DISABLE"], capture_output=True, text=True
            )
            logger.info("disabled scheduled task %r: %s", task_name, (r.stdout or r.stderr).strip())
    return done


def main(args, logger) -> None:
    if args.command == "plan":
        plan = frame.plan_cells()
        write_table(plan, frame.out_dir() / "cell_plan.csv")
        est = estimate(pd.DataFrame())
        logger.info(
            "Cells: %d to search, %d channel-not-on-YouTube\n%s",
            est["search_cells"],
            est["cells_channel_not_on_youtube"],
            plan.pivot_table(
                index=["country", "period"],
                columns="channel",
                values="plan_status",
                aggfunc=lambda s: "S" if s.iloc[0] == "search" else "-",
            ).to_string(),
        )
        logger.info("Estimate: %s", est)
        return
    if args.command == "collect":
        b = frame.Budget()
        n_before = b.searches_today()
        client = frame.YouTubeClient()
        plan = frame.plan_cells()
        plan = plan[plan["plan_status"] == "search"]
        if args.countries:
            plan = plan[plan["country"].isin(args.countries)]
        stopped = False
        for _, row in plan.iterrows():
            if args.max_searches is not None and b.searches_today() - n_before >= args.max_searches:
                stopped = True
                break
            if frame.run_search_cell(client, b, row) == "budget":
                stopped = True
                break
        logger.info(
            "search stage %s", "stopped (daily search budget)" if stopped else "complete for selected cells"
        )
        logger.info("videos.list batches: %d", frame.fetch_metadata(client, b))
        uni = frame.build_universe()
        logger.info("frozen now: %s", frame.freeze(uni))
        if not args.no_comments:
            logger.info("comment videos completed: %d", frame.fetch_comments(client, b, uni))
        uni = build(logger)
        summary(logger, uni, n_before)
        check_completion(logger, uni, args.task_name)
        return
    uni = build(logger)
    if args.command == "status":
        summary(logger, uni, frame.Budget().searches_today())


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["plan", "collect", "build", "status"])
    p.add_argument("--countries", nargs="*", help="restrict to ISO3 codes (config order kept)")
    p.add_argument("--max-searches", type=int, default=None, help="cap search requests in this run")
    p.add_argument("--no-comments", action="store_true")
    p.add_argument("--task-name", default=None, help="scheduled task to disable when collection completes")
    run_step("youtube_frame", main, p)
