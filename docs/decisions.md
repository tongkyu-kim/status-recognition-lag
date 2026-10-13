# Decision log

Dated record of methodological and infrastructure decisions. Add new entries at the bottom. Do not
rewrite past entries: supersede them with a new entry that references the old ID.

**Status values:** `adopted` · `proposed` (default until reviewed) · `open` (needs a decision) ·
`superseded by Dxxx`

Template:

```markdown
### Dxxx - Title
- **Date:** YYYY-MM-DD
- **Status:** proposed
- **Context:** why a decision is needed
- **Decision:** what was chosen
- **Alternatives:** what else was considered
- **Consequences:** what changes / what to watch
```

---

### D001 - Repository architecture and package layout
- **Date:** 2026-09-30
- **Status:** adopted
- **Context:** The analysis code must be importable by scripts, tests and notebooks without path
  hacks.
- **Decision:** A single package `srl` under `src/srl/` with the subpackages acquisition, cleaning,
  trade, status, text, attention, recognition, panel, models, figures and utils. Numbered scripts in
  `scripts/` are thin wrappers. This departs from a flat `src/<module>/` layout, where
  `import src.x` is fragile.
- **Consequences:** `pip install -e .` or `PYTHONPATH=src`. Scripts self-bootstrap via
  `scripts/_bootstrap.py`.

### D002 - Unit of analysis
- **Date:** 2026-09-30
- **Status:** proposed
- **Decision:** The primary unit is the directed dyad Korea → partner, annual. Higher frequency
  (quarterly/monthly) is a later option for attention and trade only.
- **Consequences:** Text measures are aggregated to calendar years. Split years for
  administrations need a rule.

### D003 - No automated acquisition before source validation
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** Raw data are deposited by hand under `data/raw/<source_id>/<YYYY-MM-DD>/`.
  Connectors are added only after coverage, terms and licence checks (docs/data_sources.md).
- **Consequences:** Step 01 registers and verifies files. It never downloads.

### D004 - Raw-data immutability and provenance
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** `write_table` refuses destinations inside `data/raw`. Raw files are SHA-256
  checksummed into the tracked `data/raw_manifest.csv`. `make verify-raw` detects modified,
  missing or unregistered files. The optional `--lock` flag makes registered files read-only.
- **Consequences:** Corrections to raw inputs arrive as new dated folders, never as edits.

### D005 - Recognition lag is not hard-coded
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** Approaches A (standardized difference), B (residual) and C (dynamic adjustment)
  are implemented or specified in `srl.recognition.lag` and configured as named variants in
  `config/analysis.yaml`. Sign convention: **positive = under-recognition**.

### D006 - Hypothesis tests use observed recognition as outcome
- **Date:** 2026-09-30
- **Status:** proposed
- **Context:** Regressing a status-based lag measure on status induces mechanical correlation.
  Approach B's residual is orthogonal to the fitted status terms by construction.
- **Decision:** Main models (H2–H5) use observed recognition indices as outcomes with flexible
  status-proximity terms and interactions. Lag variants are used descriptively and in robustness
  checks.

### D007 - Competitive/threat framing as a separate dimension
- **Date:** 2026-09-30
- **Status:** proposed
- **Decision:** Code `C` separately from `V`/`H`, multi-label. Recognition indices use H and V
  only. Competitive framing is a separate outcome.
- **Consequences:** H5 (catch-up with persistent concern) remains testable. "Peer" stays in the
  horizontal frame and "competitor" goes in the competitive frame.

### D008 - Recognition is relational positioning, not sentiment
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** Vertical ≠ negative and horizontal ≠ positive (coding_protocol.md §3). Sentiment,
  if measured, is a separate variable.

### D009 - Text matching rules for Korean abbreviations
- **Date:** 2026-09-30
- **Status:** proposed
- **Decision:** Only punctuated compounds (`한·중`, `한-베`) followed by a boundary are matched.
  Unpunctuated compounds (`한중`) are not, because of false positives such as `한중간`. `타이` is
  not an alias for Thailand, and bare "Timor" is not an alias for Timor-Leste. Short all-caps
  acronyms are matched case-sensitively. Demonyms are off by default.
- **Consequences:** Validate recall/precision with KWIC review on the real corpus
  (`outputs/diagnostics/mention_surface_counts.csv`) and revise.

### D010 - Outputs are regenerated, not tracked
- **Date:** 2026-09-30
- **Status:** proposed
- **Decision:** `outputs/*` is git-ignored. Final numerical outputs, tables and figures are copied
  into the replication package at release.

### D011 - Deterministic seed
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** `seed: 20260930` in `config/analysis.yaml`, used for coding samples and any
  stochastic estimation.

### D012 - No LLM dependency by default
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** `srl.recognition.llm` defines an interface only. Any LLM-assisted coding must be
  configured explicitly, with a pinned model version, a versioned prompt, stored raw outputs and
  validation against human coding.

### D013 - Main panel membership
- **Date:** 2026-09-30
- **Status:** proposed
- **Decision:** The partners are China plus all 11 ASEAN members, including Timor-Leste
  (admitted in 2025; verify date). Japan, the US and Taiwan are configured as
  `extension_candidate`, not panel members.
- **Open issues:** (a) Singapore (and, on some measures, Brunei) exceeds Korea in GDP per capita,
  so how are they treated in H2–H5? (b) Timor-Leste's sparse early data. (c) Whether HKG is
  combined with CHN in trade measures.

### D014 - Open decisions (to resolve with data in hand)
- **Date:** 2026-09-30
- **Status:** open
- Panel start/end years (`panel.start_year`, `panel.end_year`)
- Primary status proximity measure and proximity method (ratio vs. log ratio)
- Primary attention measure; treatment of ASEAN group mentions (`none` / `full` / `equal_split`)
- Whether "Southeast Asia / 동남아" references are tracked
- Text extractors for PDF/HWP/HTML sources
- Coding sample size; number of coders; masked-round share
- Small-cluster inference method
- H5 threshold and duration for "sufficiently high and sustained capability"

### D015 - Autonomous acquisition with per-source validation (supersedes D003)
- **Date:** 2026-09-30
- **Status:** adopted
- **Context:** The PI asked for autonomous retrieval of all realistically retrievable public data.
  D003 required hand deposit before any connector existed.
- **Decision:** Acquisition scripts live in `scripts/acquire/` (and `scripts/youtube/`) and use
  `srl.acquisition.fetch`: robots.txt honoured, per-host spacing (>= 1 s; 2.5-15 s for quota-limited
  APIs), backoff on 429/5xx and on Comtrade's quota 403 (Retry-After), write-once raw storage
  (`save_raw` refuses to overwrite different content), every request logged in
  `metadata/download_log.csv`. Validation (authority, access route, licence) is done per source at
  retrieval time and recorded in `config/sources.yaml` -> `metadata/source_catalog.*`. Logins, API
  keys, CAPTCHAs, guestbook/terms forms and HTTP 403 blocks are never bypassed; they become manual
  tasks (`metadata/manual_actions.yaml`).
- **Alternatives:** Keep hand deposit only (too slow for ~100k documents).
- **Consequences:** `tests/test_config.py` now checks the status contract (candidates carry no URL;
  validated sources record URL, access and licence). The raw layout `data/raw/<source_id>/<date>/`
  is kept; the brief's `raw/macro`, `raw/trade`, ... grouping is expressed through the `category`
  and `construct` fields of the catalog instead of folders.

### D016 - Income classifications: use as-announced FY classes, never recomputed ones
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** `income_classification_country_year.csv` holds the World Bank class per fiscal year
  as announced (OGHIST FY89-FY25; FY26/FY27 changes from the official notes). Event dates are the
  1 July announcement/effective dates; the GNI data year is FY-2.
- **Consequences:** Recomputing classes from the current GNI vintage disagrees in 36 panel
  country-years (data revisions, e.g. KHM FY14-16); see
  `outputs/diagnostics/income_classification_consistency.csv`.

### D017 - YouTube: minimize commenter identity at ingest
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** Before any comment resource is written to disk, `authorDisplayName`,
  `authorProfileImageUrl` and `authorChannelUrl` are dropped and `authorChannelId` is replaced by
  a salted HMAC (`authorHash`, salt in the git-ignored `.env`). The YouTube raw layer is therefore
  "API response minus commenter identity fields" - a documented exception to byte-identical raw
  storage. Publisher (channel) metadata is kept because channel type is an analytical variable.
- **Alternatives:** Keep raw identity and hash only downstream (rejected: stores personal data
  that is never needed).

### D018 - YouTube: official API only; transcripts = availability only
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** No HTML scraping or unofficial transcript libraries. `captions.list` records
  whether caption tracks exist; caption text of third-party videos is not retrievable through the
  official API (`captions.download` needs the owner's authorization). Video frames are coded from
  title + description, plus manually obtained transcripts for ambiguous cases (task Y4).

### D019 - Retrieval intent is not the coded frame (YouTube)
- **Date:** 2026-09-30
- **Status:** adopted
- **Decision:** Each search query carries a `family` (profile, upgrading, sector, competition,
  overtaking, deference, dependence) that records *why* it was run. The analytical `video_frame`
  is human-coded from content. Keeping them apart allows measuring how far provocative query
  families over-select provocative content.

### D020 - Trade sources used side by side
- **Date:** 2026-09-30
- **Status:** proposed
- **Decision:** `trade_country_year.csv` keeps Korea-reported (Comtrade), partner-reported (mirror,
  Comtrade) and Atlas-reconciled bilateral flows in separate columns. Default for interdependence:
  Korea-reported flows (full coverage 1995-2025); Atlas for product-level overlap (HS92 4-digit,
  1995-2024). Mirror data are a robustness check only (sparse for LAO, MMR, TLS).

### D021 - Government corpus: inventory for denominators, full text for alias hits
- **Date:** 2026-09-30
- **Status:** proposed
- **Decision:** For large boards (MOFA press releases/briefings, MOTIR press releases) the complete
  list inventory is kept (attention denominators), and full text is retrieved for documents the
  site's own content search returns for any partner alias. Small boards (speeches, summit pages,
  work plans) are retrieved in full. MOTIR HTML bodies are summaries (attachments hold the text),
  so MOTIR mention counts are lower bounds until task C4.
- **Consequences:** Documents that mention a partner only in a form the site search does not
  match are missing full text; estimate recall on a random sample of non-hit documents before
  using full-text attention measures.

### D022 - YouTube pilot: which videos get comments
- **Date:** 2026-09-30
- **Status:** adopted (pilot)
- **Context:** Day-1 searches returned 3,336 videos, including off-topic hits (e.g. Viet Nam War
  shorts for "베트남 한국 추월", World Cup qualifiers for Singapore). Selecting "top 40 by comment
  count" per country picked almost only 2020-26 virals.
- **Decision:** Comments are collected for videos that (a) name the country in title+description
  and (b) contain economic/status vocabulary (pattern in config/youtube_sampling.yaml ->
  comments.selection), taking the 10 most-commented per country x year bin (2010-15, 2016-19,
  2020-22, 2023-26). The screen is on topic words, never on the coded frame. `captions.list`
  (50 units/video) is deferred.
- **Consequences:** 142 pilot videos (SGP has none for 2010-15). Selection on comment count still
  favours salient videos within bins; Corpus B/C caps apply downstream. Cambodia's most-commented
  2024-26 videos concern scam compounds and crime, not economic status: Cambodia's YouTube salience
  is confounded by crime news, which must be modelled (topic control) or the case treated with care.

### D023 - YouTube sampling frame v1 supersedes the pilot design
- **Date:** 2026-09-30
- **Status:** adopted (PI instruction)
- **Decision:** Public-discourse data come from a pre-registered frame (docs/youtube_frame_protocol.md;
  config/youtube_frame.yaml): fixed whitelist of all national news broadcasters, standard Korean
  country name as the only query, identical event-relative windows around the first World Bank
  income upgrade with a full +/-24-month window after 2008-01-23, order=date census per
  country x period x channel (day-cluster probability sample for dense cells), rule-based inclusion
  with logged exclusions and manual review, seeded sampling (<= 150 per country x period), and a
  hash-stamped freeze before any comment is downloaded. The exploratory pilot (D022; relevance-ranked
  topical queries, comment-count-based selection) is retained for transparency but excluded from
  analysis. The pilot's queued comment download was cancelled before it ran.
- **Consequences:** Early windows (2008-2013) have few channels on YouTube; this is documented,
  not corrected by shifting windows.

### D024 - YouTube frame protocol v2: dense-cell trigger on observed pagination only
- **Date:** 2026-09-30 (after day-1 searches; before any frame comment download)
- **Status:** adopted
- **Context:** v1 switched a cell to a 24-day probability sample when page 1 reported
  `pageInfo.totalResults` >= 1,000. For channel- and date-filtered queries this field is
  meaningless (e.g. ~19,800 reported for CHN_P4_MBC while sampled days returned 0-1 videos).
  55 of 75 day-1 search requests went to three such cells.
- **Decision:** v2 triggers the day sample only if the census is still unfinished after 10 pages
  (500 videos). The three v1 day-sample cells continue as censuses from their cached page 1;
  their day pages are kept in raw and appear in the universe only as audit rows
  (`superseded_v1_day_sample_page`). The change depends on search behaviour only, never on comments.
- **Also observed:** every MBC/MBN cell for windows before 2012 returned zero videos. The 2010-11
  events (VNM, CHN, LAO, THA) therefore have empty pre-event windows on YouTube (PI decision
  requested; see docs/youtube_frame_protocol.md).

### D025 - Event definition confirmed by the PI
- **Date:** 2026-10-01
- **Status:** adopted
- **Decision:** Keep the pre-registered event rule (first World Bank income upgrade with a full
  +/-24-month window after 2008-01-23). For VNM, CHN, LAO and THA the pre-event windows are
  (near-)empty on YouTube; this is reported as a coverage limitation, and windows are not moved.
  Confirmed before any frame comment was downloaded.

### D026 - YouTube frame protocol v3: stricter substantive-relevance rule (PI-approved)
- **Date:** 2026-10-02 (before any frame comment download)
- **Status:** adopted
- **Context:** 350 videos were in manual review after two collection days, mostly China videos
  whose title used the headline abbreviation 中 or that named the country only in tags.
- **Decision:** (1) a title_review hanja form (中, 泰, 越) counts as the country unless glued to a
  preceding Hangul/Latin/digit character; (2) a country named only in tags is excluded as
  incidental; (3) a country named only in the description stays in manual review. Frozen samples
  are unaffected (they froze with no review items). Rule depends on titles/tags only, never on
  comments.
