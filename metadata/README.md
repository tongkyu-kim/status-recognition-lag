# metadata/

| File | Tracked in Git | Content |
|---|---|---|
| `source_catalog.csv` / `.json` | yes | One row per source: construct, status, access, URL, licence, coverage, raw-file counts. Generated from `config/sources.yaml` by `scripts/acquire/build_catalog.py` |
| `manual_actions.yaml` | yes | Source of the manual-task list (edit this) |
| `manual_actions.csv` | yes | Generated from the YAML (also renders `docs/manual_data_tasks.md`) |
| `download_summary.csv` | yes | Per-source counts of requests, outcomes and bytes, summarized from `download_log.csv` |
| `download_log.csv` | **no** (large) | Every HTTP request: timestamp, source, URL, status, destination, bytes, SHA-256, outcome |
| `youtube_quota_log.csv` | **no** | YouTube API quota ledger (units per call, quota day) |

The full logs stay on the machine that ran the collection (Dropbox-synced). They are provenance
records: do not edit them by hand.
