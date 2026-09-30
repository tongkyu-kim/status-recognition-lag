# Data

| Folder | Contents | Written by | In Git |
|---|---|---|---|
| `raw/` | Original files exactly as obtained. **Immutable.** | Hand deposit only | No |
| `interim/` | Cleaned tables in canonical schemas; text sentence/mention tables; coding samples | Scripts 02–07 | No |
| `processed/` | Analytical measures and the partner-year panel | Scripts 03, 06–08 | No |
| `external/` | Third-party reference tables (concordances, code lists, classification lists) with provenance notes | Hand deposit | No |
| `raw_manifest.csv` | SHA-256 checksum and provenance of every raw file | `make register-raw` | **Yes** |

## Raw-data layout

```text
data/raw/<source_id>/<YYYY-MM-DD>/<original file names>
```

- `<source_id>` must be a key in `config/sources.yaml`.
- `<YYYY-MM-DD>` is the retrieval date. A new retrieval goes in a new dated folder and never
  overwrites an old one.
- Add a short `README.md` in the dated folder with how the file was obtained (query parameters,
  version, notes). Keep original file names.
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
