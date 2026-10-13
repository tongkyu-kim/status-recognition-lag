"""YouTube public-discourse extension (digitally expressed public recognition).

Official YouTube Data API v3 only - no HTML scraping. See docs/youtube_data_design.md.

Modules
    api                   API client: key loading, quota ledger, privacy minimization at ingest
    queries               query plan built from config/youtube_queries.yaml + config/countries.yaml
    search_videos         search.list  -> data/raw/youtube/<date>/search/
    fetch_video_metadata  videos.list / channels.list -> .../videos/, .../channels/
    fetch_comments        commentThreads.list / comments.list -> .../comments/
    fetch_transcripts     captions.list (availability only; see module docstring)
    tables                raw -> interim tables (videos, comments) + coverage diagnostics
    deduplicate           video provenance merge; duplicate/spam comment flags
    sample_comments       corpora A-D with deterministic seeds
    classify_frames       video-frame coding sheets (+ transparent dictionary pre-screen)
"""
