# YouTube public-discourse extension: data design

Status on 2026-09-30: the pipeline is built and unit-tested. **No data has been collected yet**,
because no YouTube Data API key is configured (task Y1 in
[youtube_manual_tasks.md](youtube_manual_tasks.md)). Everything below is the design that the pilot
will test.

## 1. Theoretical purpose

The main study compares objective status with **government** recognition. This extension adds a
second audience, **digitally expressed public recognition**: how Korean-language YouTube discourse
positions partner states that are rising economically. The core comparison is

- `GovernmentRecognition_jt` (MOFA / MOTIE / presidential text; main study), against
- `PublicRecognition_jt` (YouTube comments; this extension).

The expectation is `PublicRecognitionLag > GovernmentRecognitionLag`, especially for fast-rising,
economically salient partners close to Korea in status. Additional constructs: Public Attention,
Public Recognition, Public Recognition Lag, Status Threat and Status-Claim Resistance.

**Naming.** The measure is *YouTube public discourse*, *online public status discourse* or
*digitally expressed public recognition*. It is never "Korean public opinion". YouTube commenters
are self-selected, skew by age, gender and political interest, and are shaped by platform ranking.
No population inference is made.

**Sentiment is not recognition.** "China is dangerous because its EV industry is already ahead of
ours" is negative in tone but codes as capability recognition = 1, competitive recognition = 1,
status threat = 1 and dismissal = 0. "Let's help Cambodia" is positive but is not horizontal
recognition. Coding follows [youtube_coding_protocol.md](youtube_coding_protocol.md), not a
sentiment lexicon.

## 2. Hypotheses supported by the design

| | Hypothesis | Data feature that enables the test |
|---|---|---|
| H-P1 | Government recognition adjusts faster than public recognition as partners rise | Country-year public measures alongside the government-text panel |
| H-P2 | Resistance peaks for states approaching Korea from below | Countries spread along the proximity distribution (VNM, CHN, KHM, SGP in the pilot) |
| H-P3 | Status-claim / overtaking frames draw more dismissal and mockery than neutral upgrading frames | Video-level `video_frame`; within-country-year comparison |
| H-P4 | Stronger when the partner enters Korean status-bearing industries | `industry_korean_status_bearing` on the video coding sheet (semiconductors, EV/batteries, shipbuilding, displays, autos, smartphones) |
| H-P5 | Deference reward: less resistance when the partner is portrayed as learning from Korea | `deferential` / `korean_contribution` frames. This tests a status-order mechanism, not a cultural stereotype |

## 3. Search strategy

- Queries are in Korean (`config/youtube_queries.yaml`), built from templates × the Korean country
  name in `config/countries.yaml`, with `regionCode=KR` and `relevanceLanguage=ko`.
- Generic country names alone are not searched. Every query pairs the country with economic
  status content.
- **Retrieval families** record why a query exists: `profile`, `upgrading`, `sector`,
  `competition`, `overtaking` (including status-claim wording such as 선진국, 제조업 강국, 한국 추월),
  `deference`, and `dependence`. Neutral families (profile, upgrading, sector) are always included
  so that provocative queries never make up the whole corpus (D019).
- Country-specific additions (e.g. 중국 굴기, 포스트 차이나 베트남) exist in the full tier only.
- **Time slicing.** Relevance ranking favours recent and popular uploads. For dense cases (VNM,
  CHN), selected templates are also run in time windows (`publishedAfter` / `publishedBefore`):
  two-year windows in the pilot, annual windows in the full tier.

## 4. Sampling strategy

| Level | Rule |
|---|---|
| Videos | Union of all search hits; one row per video with the full query provenance (`video_query_links`: country, family, query, rank, time window). Multi-country videos are flagged. |
| Comments collected | Up to 1,000 top-level threads per video (300 in the pilot), `order=relevance`, plus replies (up to 100 per thread) |
| Corpus A (full) | All comments; descriptive volume only |
| Corpus B (equal-video) | ≤ 200 random top-level comments per video |
| Corpus C (equal-country-year) | ≤ 1,000 random comments per country-year, drawn from B, so no single video can fill a cell |
| Corpus D (high-engagement) | Top 50 per video by likes; robustness only, never the sole sample |
| Coding sample | Stratified by country × year bin (2010–15, 2016–19, 2020–22, 2023–26) × frame stratum × engagement (top 20% vs. rest within video) |

Exclusions before B–D and before coding: non-Korean comments (Hangul share < 0.5), exact
duplicates within a video, cross-video copy-paste by the same hashed author, and texts under two
characters. All exclusions are counted in `outputs/diagnostics/youtube_sampling_log.csv`. Seeds come
from `config/youtube_sampling.yaml` (`seed: 20260930`).

## 5. API limitations and quota

| Call | Cost (units) | Notes |
|---|---|---|
| `search.list` | 100 per page (≤ 50 results) | About 500 results maximum per query; relevance-ranked, not random |
| `videos.list` / `channels.list` | 1 per 50 ids | Deleted and private videos disappear; they are recorded as `available = False` |
| `commentThreads.list` | 1 per 100 threads | Disabled comments return 403 `commentsDisabled`, recorded rather than retried |
| `comments.list` | 1 per 100 replies | |
| `captions.list` | 50 per video | Availability only; caption **text** of third-party videos is not available through the official API (D018) |

The default quota is 10,000 units per day. The pipeline keeps a 500-unit reserve, logs every call
in `metadata/youtube_quota_log.csv`, and stops cleanly (resumable) when the budget is reached.

- **Pilot (core tier):** 92 searches (56 core + 36 time-windowed) = 9,200 units → day 1. Videos,
  channels and comments for the 40 most-commented videos per country → day 2 (~1,000–2,000 units).
- **Full tier, 12 countries:** roughly 1,000 searches (≈ 10 days). Scaling beyond that needs
  Google's quota-extension audit, which is only worth requesting if the pilot passes the stop
  conditions (§10).

## 6. Coverage

Not yet observed. After the pilot, `outputs/diagnostics/youtube_coverage.csv` (country × year:
videos, comments, channels, median comments per video, Korean-comment share, status-relevant share,
duplicate rate) and `youtube_frame_coverage.csv` (country × coded frame × retrieval family) report
coverage. Both files currently contain zero rows per pilot country with an explicit "not collected"
note. Low-volume countries (BRN, TLS, LAO, MMR) may not reach usable volume; this will be reported
rather than padded.

## 7. Known biases and diagnostics

| Bias | Diagnostic / mitigation |
|---|---|
| Platform ranking (relevance / recency / popularity) | Time-windowed searches; `best_rank` and `total_results_est` kept; a later `order=date` robustness pass |
| Query-induced frame selection | Retrieval family ≠ coded frame (D019); yield per query in `youtube_query_yield.csv` |
| Viral-video dominance | Corpora B and C caps; video fixed effects |
| Channel concentration | `n_channels` per cell; channel type coding (news / economic commentary / independent creator / government-institutional); stop condition 4 |
| Commenter self-selection | Documented; no population claims |
| Bots and copy-paste | Duplicate and spam flags (hashed author × normalized text) |
| Deleted content | `available = False`; the retrieval date is stored |

## 8. Proposed variables

**Video level:** `video_id`, `countries`, `families`, `queries`, `n_query_hits`, `best_rank`, `title`,
`description`, `published_at`, `year`, `channel_id`, `channel_title`, `category_id`, `tags`,
`view_count`, `like_count`, `comment_count`, `duration_s`, `default_language`,
`default_audio_language`, `hangul_share_meta`, `caption_tracks`, `caption_langs`,
`caption_manual_ko`, `transcript_text_available`, `url`, `available`, `retrieved_utc`, `video_frame`
(human-coded, multi-label frame columns plus a primary frame), `status_claim_intensity` (0–3),
`industry_korean_status_bearing`, and `dict_*` pre-screen flags (baseline only).

**Comment level:** `comment_id`, `video_id`, `parent_comment_id`, `is_reply`, `text`,
`published_at`, `updated_at`, `like_count`, `reply_count`, `author_hash`, `hangul_share`,
`is_korean`, `dup_within_video`, `dup_same_author_cross_video`, `too_short`, and the coded categories
A–I (protocol).

**Country-year measures** (built only after validation). Approach D, multidimensional, is the
default: separate shares of capability recognition, horizontal recognition, competitive
recognition, dismissal, attribution discounting, status threat and mockery among status-relevant
comments. Approaches A (recognition share), B (recognition minus dismissal) and C
(attribution-adjusted recognition) are computed side by side.

**Public recognition lag and the elite–public gap** are not computed until the public measure is
validated. Once it is: `PublicRecognitionLag_jt = E[Recognition | ObjectiveStatus_jt] -
ObservedPublicRecognition_jt` and `ElitePublicGap_jt = GovernmentRecognition_jt -
PublicRecognition_jt`, on a common scale, with the same caveats as D006 (use observed recognition as
the outcome in models).

## 9. Identification opportunities

These are designs, not causal claims. Each depends on assumptions checked in the pilot.

- **Within-country-year frame contrasts:** comments under differently framed videos about the same
  country in the same period (country × year FE). The unit is the comment, with clustering by video.
- **Within-channel variation:** channels that publish both neutral and overtaking-framed videos
  (channel FE). This holds audience composition roughly constant.
- **Controls:** video popularity (log views), topic / sector, video age at retrieval, and comment
  position (rank under relevance order).
- **Event windows:** comments on videos published around salient status events. Examples are the
  income-class upgrades (VNM and PHL to upper-middle income, 1 July 2026; the timeline is in
  `data/interim/prelim/event_transitions.csv`), major investment announcements and
  overtaking headlines. Upload timing is endogenous to events, so these are descriptive
  event-time profiles unless a design isolates exposure.

## 10. Pilot and stop conditions

Pilot countries: Viet Nam, China, Cambodia, Singapore (`config/youtube_queries.yaml` → `pilot`).

Steps: (1) run the core search set; (2) retrieve video and channel metadata; (3) inspect coverage by
year, channel, query and family; (4) collect comments for the 40 most-commented videos per country;
(5) build tables and diagnostics; (6) **manually inspect and code 100–200 comments per major case**
(task Y2) before scaling.

Do **not** scale to the full corpus unless all five conditions hold:

1. enough Korean-language comments exist (target ≥ 1,000 eligible comments per major case per
   year bin);
2. theory-relevant frames are present (≥ 3 of the video frames observed per major case);
3. recognition, dismissal, attribution discounting, threat and mockery can be coded reliably
   (Krippendorff's α ≥ 0.67 per category on the double-coded overlap, or a documented merge of
   unreliable categories);
4. coverage is not dominated by one or two channels (top-2 channels < 50% of eligible comments per
   country);
5. the API quota supports collection (the full tier fits within the approved daily quota over a
   reasonable window).

If any condition fails, the failure is reported in `docs/youtube_collection_status.md` and the
construct or sampling is revised. The design is not forced.

## 11. Ethics, privacy and terms

- Official API only; quotas and rate limits are respected; no HTML scraping (D018).
- Commenter display names, profile images and channel URLs are never stored; commenter channel
  ids are hashed at ingest with a private salt (D017). No demographic inference and no
  de-anonymization.
- Analytical outputs do not reproduce usernames. Quotations in publications are paraphrased or
  kept to short excerpts that cannot be searched back to the author.
- YouTube API Services Terms and Developer Policies: data must be kept current and deleted or
  refreshed on request. Public replication releases therefore contain comment IDs and derived
  labels, not the raw comment corpus.
- The raw YouTube layer stays local, is git-ignored, and is excluded from any sharing.

## 12. Code map

| Step | Module / script |
|---|---|
| Query plan and quota estimate | `src/srl/youtube/queries.py` (`run_youtube.py plan`) |
| Search | `src/srl/youtube/search_videos.py` |
| Video / channel metadata | `src/srl/youtube/fetch_video_metadata.py` |
| Comments | `src/srl/youtube/fetch_comments.py` |
| Caption availability | `src/srl/youtube/fetch_transcripts.py` |
| Tables and diagnostics | `src/srl/youtube/tables.py`, `deduplicate.py` |
| Corpora and coding samples | `src/srl/youtube/sample_comments.py`, `classify_frames.py` |
| CLI | `scripts/youtube/run_youtube.py` |
| Tests | `tests/test_youtube.py` |
