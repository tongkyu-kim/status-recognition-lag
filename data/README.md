# Data

| Folder | Contents | Written by | In Git |
|---|---|---|---|
| `raw/` | Original files exactly as obtained. **Immutable.** | `scripts/acquire/*`, `scripts/youtube/*` (write-once) or hand deposit | No |
| `interim/` | Cleaned tables in canonical schemas; `prelim/` low-risk derived files (macro, trade, income classes, events, government document table); `youtube/`; text tables; coding samples | Scripts 02–07, `scripts/acquire/build_*.py`, `scripts/youtube/run_youtube.py` | No |
| `processed/` | Analytical measures and the partner-year panel | Scripts 03, 06–08 | No |
| `external/` | Third-party reference tables (concordances, code lists, classification lists) with provenance notes | Hand deposit | No |
| `raw_manifest.csv` | SHA-256 checksum and provenance of every raw file | `make register-raw` | **Yes** |

## Preliminary derived files (`interim/prelim/`)

| File | Unit | Built by |
|---|---|---|
| `macro_country_year.csv` | country-year (WDI + Atlas ECI) | `scripts/acquire/build_prelim.py` |
| `income_classification_country_year.csv` | country-fiscal year (World Bank) | same |
| `trade_country_year.csv` | Korea-partner-year (Comtrade reporter/mirror + Atlas) | same |
| `trade_product_country_year.csv/.parquet` | country-HS4-year exports, RCA, PCI (Atlas) | same |
| `trade_bilateral_product_year.parquet` | Korea-partner-HS4-year flows (Atlas) | same |
| `event_transitions.csv` | formal status events (with `verification`) | same |
| `gov_documents_korea.csv` | Korean government document (metadata; text in `interim/text/`) | `scripts/acquire/build_gov_documents.py` |

No proximity, convergence, composite or recognition variables are built at this stage.

Provenance: `metadata/source_catalog.*` (sources), `metadata/download_log.csv` (every request),
`metadata/manual_actions.*` (human tasks), `data/raw_manifest.csv` (checksums).

## Raw-data layout

```text
data/raw/<source_id>/<YYYY-MM-DD>/<original file names>
```

- `<source_id>` must be a key in `config/sources.yaml`.
- `<YYYY-MM-DD>` is the retrieval date. A new retrieval goes in a new dated folder and never
  overwrites an old one.
- Add a short `README.md` in the dated folder with how the file was obtained (query parameters,
  version, notes). Keep original file names. Acquisition scripts write this README themselves.
- Exception (D017): YouTube comment resources are stored with commenter identity fields removed
  and commenter channel ids hashed at ingest.
- After depositing, run `make register-raw` (or `python tasks.py register-raw`).

## Government-text deposit format

Each dated folder of a `government_text` source contains the documents (currently `.txt` in UTF-8;
extractors for PDF/HWP/HTML still need to be chosen) and a `metadata.csv` sidecar:

| column | required | description |
|---|---|---|
| `doc_id` | yes | Stable identifier unique within the source |
| `file` | yes | File name relative to the folder |
| `title` | yes | Title as published |
| `date` | yes | Publication date, `YYYY-MM-DD` |
| `institution` | yes | Issuing body |
| `doc_type` | yes | `press_release`, `speech`, `joint_statement`, `white_paper`, `minutes`, `briefing`, `other` |
| `language` | no | `ko` / `en` (detected if empty) |
| `original_url` | no | The URL the file was actually obtained from |
| `notes` | no | Free text |

## Rules

- Never edit or delete raw files. Corrections are new files.
- Do not commit data. `.gitignore` and a pre-commit hook enforce this.
- The repository sits in a synced folder (Dropbox). Avoid editing the same files on several
  machines at once, and keep a Git remote as the canonical history.
