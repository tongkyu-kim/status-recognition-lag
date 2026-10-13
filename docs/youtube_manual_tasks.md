# YouTube extension: manual tasks

The master list of all manual tasks is [manual_data_tasks.md](manual_data_tasks.md) (generated from
`metadata/manual_actions.yaml`). The YouTube tasks are repeated here with pilot-specific detail.

## Y1: API key setup (HIGH, blocks everything)

1. Go to <https://console.cloud.google.com/>, create a project (e.g. `status-recognition-lag`).
2. APIs & Services → Library → **YouTube Data API v3** → Enable.
3. APIs & Services → Credentials → Create credentials → **API key**. Restrict it: API restrictions →
   YouTube Data API v3 only.
4. In the repository root, create a file named `.env` (it is git-ignored) with one line:
   `YOUTUBE_API_KEY=<your key>`.
5. Day 1: `python scripts/youtube/run_youtube.py plan search --pilot --run 2026-10-01`
   (92 searches = 9,200 units).
6. Day 2 (after the quota resets at midnight US Pacific time):
   `python scripts/youtube/run_youtube.py videos channels comments build sample --pilot --run 2026-10-01`.
   Use the same `--run` date so the collection resumes in the same raw folder.

The first comment collection automatically creates a private hashing salt (`SRL_HASH_SALT`) in
`.env`. **Back up `.env` privately**: author hashes are only comparable across runs that use the
same salt.

## Quota increase (only if the pilot passes the stop conditions)

The default quota is 10,000 units per day. The full 12-country tier needs about 10 days at that
quota. Request more through the YouTube API Services audit and quota-extension form (linked
from the quota page of the Google Cloud console). The form asks for a description of the use case:
academic research, official API only, no redistribution of raw comments, and data minimization.

## Y2: manual inspection and coding (HIGH, pilot gate)

After the pilot build, `data/interim/coding_samples/youtube_comment_coding_sheet.csv` holds up to
200 stratified comments per country. Code VNM and CHN first, following
[youtube_coding_protocol.md](youtube_coding_protocol.md). Two coders code a shared 50-comment
subset. Save the returned sheets as new files under `data/raw/human_coding/<date>/` (raw and
immutable) and report α in `docs/youtube_collection_status.md`.

## Y3: video frame coding (MEDIUM)

Use `data/interim/coding_samples/youtube_video_coding_sheet.csv`. The `dict_*` columns in
`data/interim/youtube/videos_prescreen.parquet` are unvalidated keyword flags. Do not copy them
into the frame columns.

## Y4: transcripts for ambiguous videos (LOW)

The official API cannot return caption text for other people's videos (D018). For videos whose
frame cannot be decided from title and description, open the video → "…" → *Show transcript*, copy
the text into `data/raw/youtube_transcripts_manual/<date>/<video_id>.txt`, and note the video id on
the coding sheet.

## Ambiguous frame classifications

After Y3, list the videos where coders disagreed on `frame_primary` or set `uncertain = 1` in
`docs/youtube_collection_status.md`, and resolve them in a joint session before any frame-based
comparison (H-P3 to H-P5).
