# Overnight research results

2026-10-14. Full narrative log: `outputs/reports/overnight_execution_log.md`. Manuscript:
`outputs/manuscript/manuscript_exploratory.md`.

## A. Executive summary

Acquired a genuinely new 10,742-speech Japanese Diet corpus (1980-2024, the first recognition-
side data this project has ever had for the Japan→Korea direction), reused the existing Korean
government corpus for Korea→China, and produced 343 single-pass LLM-assisted R0-R5 recognition
classifications (175 Japan-Korea, 168 Korea-China) across stratified samples spanning both
corpora's full date ranges. Audited the prior session's three industrial crossover candidates,
catching and excluding two unreliable ones (display/LCD proxy; pre-1992 shipbuilding SITC break)
that were not previously screened this carefully. Built period-level recognition time series and
compared them against the three verified crossover dates, producing one directly quotable,
individually-read finding (a 2008 Diet quote understating Korea's already-passed shipbuilding
lead, vs. a 2020 quote fully conceding it) that is this session's strongest single piece of
evidence for the central hypothesis. Investigated but did not acquire survey microdata (EAI/
Genron, Pew) -- access terms documented, not incorporated into analysis. Did not implement a
validated classifier, a human-coding pass, a fitted turning-point model, or the US→Japan
historical extension.

## B. Data acquisition

| Source | Coverage | N | Status | Output path |
|---|---|---|---|---|
| NDL Diet Record API (new) | JPN Diet speeches, 1980-2024, Korea + economy/competition/catchup queries | 10,742 speeches (deduplicated); 5,594 Korea-mentioning + economically relevant sentences | acquired, built, sampled, partially classified | `data/raw/jp_diet/2026-10-14/`, `data/interim/text/jp_diet_speeches.parquet` |
| Korean gov't corpus (legacy, reused) | kr_mofa/kr_motie/kr_presidential_office, China mentions | 32,423 China-mentioning sentences (pre-existing); 300 sampled this session | reused, sampled, partially classified | `data/annotations/kor_chn_recognition_sample.csv` |
| Atlas of Economic Complexity (legacy, reused) | HS92/SITC export data, USA/JPN/KOR/CHN | ~260 raw files (pre-existing) | reused for crossover audit | `data/processed/industrial_crossover_candidates.csv` |
| Japan MOFA press archive | -- | -- | BLOCKED, HTTP 403 (confirmed, matches prior session's finding) | `docs/data_access_requirements.md` |
| Kantei (PM's Office) press briefings | Chief Cabinet Secretary daily briefings | -- | accessible (no robots.txt restriction found), historical depth beyond ~20 days NOT confirmed; not acquired this session | `docs/data_access_requirements.md` |
| EAI/Genron survey | Korea-Japan status-perception items | -- | access terms investigated (prior session); raw microdata access NOT confirmed; not acquired | `docs/data_access_requirements.md` |
| CEPII BACI | HS6 bilateral trade | -- | confirmed freely downloadable, NOT downloaded this session | `docs/data_access_requirements.md` |

## C. New empirical findings

**Exploratory, not validated** (see D and the manuscript's limitations section for exactly what
that means here):

1. Japan's elite discourse continued framing Korea as "catching up"/"right behind" in shipbuilding
   as late as 2008, six years after Korea's export-share crossover (~2002); full concession
   ("top share until the 1990s... largely taken") does not appear until a 2020 quotation in the
   sample. Individually read, directly quotable, high-confidence as a qualitative finding; the
   quantitative period series around it (peer share flat at 0.30-0.36 through 2000-2015, rising to
   0.67 by 2020-23) is directional only given n=3-14 per period.
2. Korea's recognition of China peaked (peer share 0.75) in 2008-11 and *declined* to 0.22 by
   2020-23 as competitive-threat framing rose concurrently -- a non-monotonic pattern the brief's
   multi-component framework anticipates better than a single-lag model.
3. Audited the shipbuilding, semiconductor, and battery crossovers from the prior session; found
   and excluded two unreliable results (pre-1992 SITC shipbuilding, HS9013 display proxy) that had
   not previously been checked against independent industry history this closely.

## D. Recognition measurement

- **Coding strategy:** R0 (no attribution) through R5 (explicit challenger superiority), plus
  dismissive/stereotyping/threat-coexists/direction-mismatch flags. Full scheme in
  `docs/measurement_protocol.md`.
- **Usable passages classified:** 175/200 of the Japan-Korea stratified sample; 168/300 (169 raw,
  one excluded for direction mismatch is counted within the 168, see data file) of the Korea-China
  stratified sample. Remaining unclassified items in both samples are real, sampled, available for
  continuation -- not a data gap, a time-budget stopping point.
- **Model/method used:** this agent (Claude Sonnet 5), single pass, reading each passage directly
  and writing a one-line justification per item (visible in the `notes` column of
  `data/interim/recognition/*_llm_classified.csv`). No embeddings/supervised/dictionary backend
  was implemented or compared.
- **Validation evidence available:** none. No human-coded reference labels exist for any item in
  either sample. Inter-rater reliability, precision, recall, and F1 are all unmeasured and must
  not be reported until a human-coding pass exists.
- **Known errors caught and fixed this session:** a CSV-quoting bug that corrupted 2 rows of the
  Korea-China classification file (unescaped commas in free-text notes) was found via a downstream
  parser error and repaired (`git log`, the repair script's output is in the execution log); an
  item-indexing slip produced one duplicate/placeholder row in the Japan-Korea file, caught by
  inspection and corrected before the file was used in any analysis.
- **Human annotation still required:** all 343 classified items (plus the ~232 sampled-but-not-yet-
  classified items in both annotation-ready files) need independent human coding against the same
  R0-R5 scheme before any precision/validity claim can be made.

## E. Recognition turning points

| Case | Industry | Material crossover (T1) | Recognition transition (T3) | Estimated lag | Uncertainty / limitation |
|---|---|---|---|---|---|
| JPN→KOR | Shipbuilding | ~2002 (reliable) | Not formally estimated; bracketed qualitatively between a 2008 quote (not yet conceded) and a 2020 quote (fully conceded) | ~10-18 years (bracket, not a point estimate) | No change-point model fit; period series is descriptive only, n too small for a formal estimate |
| JPN→KOR | Batteries | ~2010 (reliable) | **Recognition transition not identifiable from available data** | -- | Insufficient classified sentences specifically on batteries to bracket a transition |
| JPN→KOR | Semiconductors | ~2013 (reliable) | **Recognition transition not identifiable from available data** | -- | Same |
| KOR→CHN | Batteries | ~1996 (reliable, but a divergent-growth pattern, not a reversal of established KOR leadership) | **Recognition transition not identifiable from available data** | -- | Peer share was already rising before 1996; no clean pre/post break found |
| KOR→CHN | Shipbuilding | ~2021 (moderate reliability, short window) | **Recognition transition not identifiable from available data** | -- | Too recent; insufficient post-crossover classified sentences |
| KOR→CHN | Semiconductors | Explicitly excluded as a T1 candidate | -- | -- | Export value conflates capability with assembly/re-export (decision_log R003) |

Per the brief's explicit instruction, no date above is guessed where the data do not support one.

## F. Research feasibility

1. **Japan-Korea historical recognition analysis:** now feasible for the first time (corpus
   exists) but not yet validated. Feasible to extend (more of the 200-item sample, or a larger
   draw from the 5,594-sentence relevant pool) without new acquisition.
2. **Korea-China comparative recognition analysis:** feasible, corpus already existed; this
   session added the first R0-R5-scheme classifications on top of it.
3. **US-Japan historical extension:** NOT feasible yet. No media/recognition corpus exists for
   either side; only material-status data (WDI, Atlas) exist, as before this session.
4. **Direct public-opinion validation:** NOT feasible yet. Survey access terms are documented
   (`docs/data_access_requirements.md`) but no survey data (microdata or even transcribed report
   tables) were incorporated this session.
5. **Cross-domain social-recognition analysis:** NOT attempted this session. Marriage-statistics
   access points found in the prior session remain unexploited.

## G. Blockers

- Japan MOFA press archive: HTTP 403, confirmed blocked (not a credentials issue -- likely a bot
  defense). No workaround attempted, per the brief's explicit instruction not to bypass access
  restrictions.
- EAI/Genron, Pew microdata: access mechanics unconfirmed; requires a direct inquiry/registration
  only you can authorize or complete.
- No human coder available in this session: the single most important blocker for turning any
  finding in Section C above from "exploratory" to "validated."
- Kantei press-briefing historical depth: this session confirmed the recent archive is reachable
  but did not find the mechanism for browsing years before ~20 days back; needs either more
  URL-pattern investigation or a different access route.

## H. Research priorities (ranked)

1. **Human-code a sample of the 343 already-classified items** (or a subset) against the same
   R0-R5 scheme to get a first inter-rater reliability estimate -- this is the single highest-
   leverage next step, since every finding in this report is currently unvalidated.
2. **Classify the remaining ~25 unclassified Japan-Korea and ~132 unclassified Korea-China sample
   items**, particularly the battery- and semiconductor-specific sentences, so the two crossovers
   without any bracketed recognition transition (Section E) can be investigated.
3. **Acquire a second Japanese recognition source** (Kantei press briefings, or a licensed
   newspaper-archive export per the brief's import-interface instruction) to check whether the
   Diet-speech pattern replicates outside parliamentary debate specifically.
4. **Resolve EAI/Genron and Pew data access** (a direct inquiry) -- the highest-value survey
   source given it is already precedented in peer-reviewed use for exactly this kind of question
   (Kim 2025, verified in the prior session).
5. **Fit a formal turning-point model** (segmented regression or change-point detection) once (1)
   and (2) above give a large-enough, validated series to support one -- not before.

## I. Reproducibility

- New/changed scripts: `scripts/acquire/acq_jp_diet_fulltext.py`, `build_jp_diet_corpus.py`;
  `scripts/exploratory/sample_recognition_passages.py`, `sample_jp_kor_recognition_passages.py`,
  `build_recognition_timeseries.py`, `industrial_crossover_detection.py` (fixed/portable),
  `historical_overlap_chain.py` (fixed/portable).
- New source code: `src/srl/text/segmentation.py:split_sentences_ja` (tested,
  `tests/test_segmentation_ja.py`, 4/4 passing).
- Tests: full suite run before and after this session's changes -- **84/84 passing** (80 prior +
  4 new `split_sentences_ja` tests this session).
- Dependencies: no new Python packages required (pandas/matplotlib/pyyaml, already installed).
- Output locations: `data/raw/jp_diet/2026-10-14/`, `data/interim/text/jp_diet_speeches.parquet`,
  `data/interim/recognition/*.csv`, `data/annotations/*.csv`, `data/processed/
  industrial_crossover_candidates.csv` (updated reliability notes unchanged from prior session),
  `outputs/exploratory/*.{csv,png}`, `outputs/manuscript/manuscript_exploratory.md`.
- **Explicitly NOT implemented this session** (do not infer otherwise from any file existing):
  a validated classifier of any kind; a human-coding interface beyond the existing empty-column
  CSV format; survey-data ingestion code; a fitted statistical turning-point model; any US-Japan
  recognition-side data.
