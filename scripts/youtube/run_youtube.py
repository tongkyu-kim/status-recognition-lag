"""YouTube extension pipeline (official YouTube Data API v3 only).

Stages (run in order; every stage is resumable and quota-aware):
    plan       build the search plan + quota estimate (no API key needed)
    search     search.list for the plan                       (100 units / page)
    videos     videos.list for all retrieved ids              (1 unit / 50 videos)
    channels   channels.list for all publishing channels      (1 unit / 50 channels)
    captions   captions.list -> transcript availability only  (50 units / video)
    comments   commentThreads.list (+ comments.list replies)  (1 unit / 100 comments)
    build      raw -> interim tables, duplicate flags, coverage diagnostics
    sample     corpora A-D + stratified coding sample + coding sheets

Examples
    python scripts/youtube/run_youtube.py plan --pilot
    python scripts/youtube/run_youtube.py search --pilot --run 2026-10-01
    python scripts/youtube/run_youtube.py videos channels comments build sample --pilot --run 2026-10-01

``--run`` fixes the raw collection folder data/raw/youtube/<run>/ across days (quota resets daily).
"""

import argparse
import json
import os

import _bootstrap  # noqa: F401
import pandas as pd

from srl.utils.cli import run_step
from srl.utils.config import get_path, load_config
from srl.utils.io import write_table

STAGES = ["plan", "search", "videos", "channels", "captions", "comments", "build", "sample"]


def main(args, logger) -> None:
    if args.run:
        os.environ["SRL_YT_RUN"] = args.run
    from srl.youtube import api, queries

    diag = get_path("outputs.diagnostics", mkdir=True)
    plan = queries.build_plan(args.countries or None, pilot=args.pilot)

    if "plan" in args.stages:
        df = pd.DataFrame([{**s.__dict__, "spec_id": s.spec_id} for s in plan])
        write_table(df, diag / "youtube_search_plan.csv")
        est = queries.quota_estimate(plan, args.max_pages)
        logger.info(
            "Search plan: %d searches; %d units; ~%d day(s) at the default quota",
            est["n_searches"],
            est["search_units"],
            est["days_at_default_quota"],
        )
        logger.info("By country/family:\n%s", df.groupby(["country", "family"]).size().unstack(fill_value=0))

    needs_api = [s for s in args.stages if s in ("search", "videos", "channels", "captions", "comments")]
    client = api.YouTubeClient() if needs_api else None  # raises MissingCredential without a key
    if client:
        logger.info("Quota remaining today (budget minus reserve): %d units", client.ledger.remaining())
    if "search" in args.stages:
        from srl.youtube.search_videos import run_search

        logger.info("search: %s", run_search(client, plan, max_pages=args.max_pages))
    if "videos" in args.stages:
        from srl.youtube.fetch_video_metadata import fetch_videos

        logger.info("videos.list batches: %d", fetch_videos(client))
    if "channels" in args.stages:
        from srl.youtube.fetch_video_metadata import fetch_channels

        logger.info("channels.list batches: %d", fetch_channels(client))
    if "captions" in args.stages or "comments" in args.stages:
        from srl.youtube.fetch_comments import select_videos

        per_country = (
            load_config("youtube_queries")["pilot"]["comments"]["max_videos_per_country"]
            if args.pilot
            else None
        )
        ids = select_videos(per_country=per_country)
        if args.max_videos:
            ids = ids[: args.max_videos]
        logger.info("%d videos selected for captions/comments", len(ids))
    if "captions" in args.stages:
        from srl.youtube.fetch_transcripts import fetch_caption_availability

        logger.info("captions.list: %d videos", fetch_caption_availability(client, ids))
    if "comments" in args.stages:
        from srl.youtube.fetch_comments import fetch_comments_for

        res = fetch_comments_for(client, ids, pilot=args.pilot)
        logger.info(
            "comments: %d videos processed; statuses %s",
            len(res),
            pd.Series([r["status"] for r in res]).value_counts().to_dict() if res else {},
        )

    if "build" in args.stages or "sample" in args.stages:
        from srl.youtube import deduplicate, tables

        run_dir = api.raw_root()
        links = tables.build_link_table(run_dir)
        videos = tables.build_video_table(run_dir, links) if not links.empty else pd.DataFrame()
        comments = deduplicate.flag_duplicates(tables.build_comment_table(run_dir))
        out = tables.interim_dir()
        note = "" if not links.empty else "not collected: YouTube Data API key not configured (task Y1)"
        if not links.empty:
            write_table(links, out / "video_query_links.parquet")
            write_table(videos, out / "videos.parquet")
        if not comments.empty:
            write_table(comments, out / "comments.parquet")
        countries = args.countries or load_config("youtube_queries")["pilot"]["countries"]
        cov, frames = tables.coverage_tables(videos, comments, links, countries, note)
        write_table(cov, diag / "youtube_coverage.csv")
        write_table(frames, diag / "youtube_frame_coverage.csv")
        if not links.empty:
            qy = (
                links.groupby(["country", "family", "query"])
                .agg(
                    n_results=("video_id", "size"),
                    n_unique=("video_id", "nunique"),
                    total_results_est=("total_results_est", "max"),
                )
                .reset_index()
            )
            write_table(qy, diag / "youtube_query_yield.csv")
        logger.info(
            "build: %d links, %d videos, %d comments (dup rate %.3f)",
            len(links),
            len(videos),
            len(comments),
            deduplicate.duplicate_rate(comments),
        )

        if "sample" in args.stages and not comments.empty:
            from srl.youtube import classify_frames, sample_comments

            corpora, log = sample_comments.build_corpora(comments, videos)
            for name, df in corpora.items():
                write_table(df, out / f"corpus_{name}.parquet")
            write_table(log, diag / "youtube_sampling_log.csv")
            sample = sample_comments.coding_sample(comments, videos)
            coding_dir = get_path("interim.coding_samples", mkdir=True)
            write_table(
                classify_frames.comment_coding_sheet(sample, videos),
                coding_dir / "youtube_comment_coding_sheet.csv",
            )
            vids = classify_frames.dictionary_prescreen(videos[videos["available"].fillna(False)])
            write_table(vids, out / "videos_prescreen.parquet")
            write_table(
                classify_frames.video_coding_sheet(vids), coding_dir / "youtube_video_coding_sheet.csv"
            )
            logger.info(
                "sample: corpora %s; coding sample %d",
                json.dumps(log.set_index("corpus")["n_comments"].to_dict()),
                len(sample),
            )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("stages", nargs="+", choices=STAGES)
    p.add_argument(
        "--pilot", action="store_true", help="pilot countries/families (config/youtube_queries.yaml)"
    )
    p.add_argument("--countries", nargs="*", help="ISO3 codes (default: pilot or full panel)")
    p.add_argument("--run", help="collection run folder YYYY-MM-DD (default today)")
    p.add_argument("--max-pages", type=int, default=1, help="search pages per query (100 units each)")
    p.add_argument("--max-videos", type=int, default=None, help="cap videos for captions/comments")
    run_step("youtube", main, p)
