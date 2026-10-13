# YouTube collection status

**As of 2026-09-30: nothing collected.** The YouTube Data API v3 requires an API key, none is
configured in this environment, and the project does not scrape YouTube HTML (D018). The pilot
therefore could not run. Coverage is reported as zero rather than estimated.

| Item | Status |
|---|---|
| Countries collected | none (pilot targets: VNM, CHN, KHM, SGP) |
| Videos collected | 0 |
| Comments collected | 0 |
| Temporal coverage | none |
| Failed API calls | none attempted (`MissingCredential` raised before any call) |
| Quota used | 0 units (`metadata/youtube_quota_log.csv` not yet created) |
| Diagnostics files | `outputs/diagnostics/youtube_coverage.csv` and `youtube_frame_coverage.csv` exist with zero rows per pilot country and the note "not collected: YouTube Data API key not configured (task Y1)" |
| Search plan | `outputs/diagnostics/youtube_search_plan.csv`: 92 pilot searches (56 core + 36 two-year-window searches for VNM and CHN) = 9,200 quota units |

## What is ready

- Query dictionary with retrieval families (`config/youtube_queries.yaml`) and sampling, quota and
  privacy rules (`config/youtube_sampling.yaml`).
- Resumable, quota-aware collectors for search, videos, channels, comments (with replies) and
  caption availability. Commenter identity is minimized at ingest.
- Table builders, duplicate and spam flags, Korean-language detection, corpora A–D, stratified
  coding samples, video and comment coding sheets, and coverage diagnostics.
- Tests with mocked API responses (`tests/test_youtube.py`, 7 tests).

## Stop-condition checklist (fill in after the pilot)

| # | Condition | Threshold (docs/youtube_data_design.md §10) | Result |
|---|---|---|---|
| 1 | Enough Korean-language comments | ≥ 1,000 eligible per major case per year bin | not yet observed |
| 2 | Theory-relevant frames present | ≥ 3 frames per major case | not yet observed |
| 3 | Reliable coding | α ≥ 0.67 per category (after one revision) | not yet observed |
| 4 | Not dominated by 1–2 channels | top-2 channels < 50% of eligible comments | not yet observed |
| 5 | Quota feasible | full tier within approved quota | 9,200 units for pilot searches; full tier ≈ 10 days at default quota |

## Next action

The PI is applying for the API key (2026-09-30). Once it is in `.env`, follow task Y1 in [youtube_manual_tasks.md](youtube_manual_tasks.md), then the two-day pilot.
