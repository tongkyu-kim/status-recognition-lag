# YouTube sampling frame v1: pre-registered protocol

Fixed on **2026-09-30, before any frame search was executed**. The machine-readable version is
`config/youtube_frame.yaml`; its SHA-256 is stored with every freeze record. Code:
`src/srl/youtube/frame.py`, `scripts/youtube/run_frame.py`; tests: `tests/test_youtube_frame.py`.
Collection outputs and the generated README are in `data/processed/youtube_frame/`.

This frame **replaces** the exploratory pilot (relevance-ranked topical queries, comment-count-based
video choice; D022). Pilot files in `data/raw/youtube/2026-09-30/` are kept but are not part of the
frame (D023).

## 1. Channel whitelist

The criterion is not a hand-picked subset: every Korean national broadcaster with a news licence
(3 terrestrial networks, 2 twenty-four-hour news channels, 4 general-programming channels), each via
its official news channel.

| key | channel | channel id | type | on YouTube since |
|---|---|---|---|---|
| KBS | KBS News | UCcQTRi69dsVYHN3exePtZ1A | terrestrial | 2013-08-06 |
| MBC | MBCNEWS | UCF4Wxdo3inmxP-Y59wXDsFw | terrestrial | 2006-11-05 |
| SBS | SBS 뉴스 | UCkinYTS9IHqOEwR1Sze2JTw | terrestrial | 2014-05-02 |
| YTN | YTN | UChlgI3UHCOnwUGzWzbJ3H5w | 24h news | 2013-05-23 |
| YONHAPTV | 연합뉴스TV | UCTHCOPwqNfZ0uiKOvFyhGwg | 24h news | 2015-01-05 |
| JTBC | JTBC News | UCsU-I-vHLiaMfV_ceaYz5rQ | general programming | 2012-02-21 |
| TVCHOSUN | 뉴스TVCHOSUN | UCWlV3Lz_55UaX4JsMj-z__Q | general programming | 2012-08-23 |
| CHANNELA | 채널A News | UCfq4V1DAuaojnr2ryvWNysw | general programming | 2012-05-21 |
| MBN | MBN News | UCG9aFJTZ-lMCHAiO1KJsirg | general programming | 2006-03-05 |

The channel ids came from cached `channels.list` responses, at no extra quota.

## 2. Country-name dictionary

| ISO3 | search term (only) | title forms that auto-include | title forms → manual review |
|---|---|---|---|
| VNM | 베트남 | 베트남, 월남, 한-베, 한·베 | 越 |
| CHN | 중국 | 중국, 한중, 미중, 한·중, 한-중, 韓中, 美中, 中國 | 中 (also means "during") |
| LAO | 라오스 | 라오스 | – |
| THA | 태국 | 태국 | 泰 |
| MMR | 미얀마 | 미얀마, 버마 | – |
| KHM | 캄보디아 | 캄보디아 | – |
| IDN | 인도네시아 | 인도네시아, 인니 | – |

No issue keywords are used. The same single-term rule applies to every country.

## 3. Events and windows

**Event rule (a priori):** for each partner, the first World Bank income-group **upgrade**
(effective 1 July) whose full ±24-month window lies between YouTube's Korean launch (2008-01-23) and
the collection date. This gives VNM 2010-07-01, CHN 2011-07-01, LAO 2011-07-01, THA 2011-07-01,
MMR 2015-07-01, KHM 2016-07-01 and IDN 2020-07-01. Not eligible: TLS (window would start 2006), MYS
(1993), SGP and BRN (no change), and PHL/VNM FY27 (2026-07-01; post-windows end in 2028, so they are
a scheduled extension).

**Windows (identical for every case, months relative to the event month; month 0 excluded):**
P1 = −24..−13, P2 = −12..−1, P3 = +1..+12, P4 = +13..+24, as calendar months in Korea time.

## 4. Search rule

One cell = country × period × channel. Each cell runs `search.list` with `q=<country name>`,
`channelId`, `type=video`, `order=date`, `maxResults=50`, a fixed `publishedAfter`/`publishedBefore`,
and `regionCode=KR`. It is paginated to exhaustion. Past YouTube's ~500-result cap, the same query
continues with a date cursor, so each cell is a **census** of search-retrievable videos.

**Dense-cell rule** (identical for all cells): if page 1 reports ≥ 1,000 results, or census
pagination reaches 20 pages, the cell switches to a **day-cluster probability sample**. 24 calendar
days (KST) are drawn with a seed and each day is searched to exhaustion. Inclusion probability =
24 / days in window. Probe pages stay in the audit files as excluded
(`dense_cell_probe_not_in_probability_sample`).

Cells whose window ends before the channel opened on YouTube are recorded as
`channel_not_on_youtube` and are never searched (93 of 252 cells).

## 5. Inclusion rules (applied in order; every exclusion is logged with its reason)

1. Channel in the whitelist.
2. Published inside the window (KST).
3. Korean language: `defaultAudioLanguage`/`defaultLanguage` starts with `ko`, or ≥ 50% of the
   title's letters are Hangul.
4. Format: 61 s ≤ duration ≤ 60 min; not `#shorts`; not live or upcoming.
5. Substantive discussion:
   - country form in the **title** → included;
   - an ambiguous title form, or the country only in description/tags → **manual review**;
   - the country absent from title, description and tags → excluded (incidental match).

Videos are never excluded for sentiment, framing, views, comment volume or political convenience.

## 6. Sampling, freezing and comments

- **Per country × period (pooled over channels):** a census if N ≤ 150 included videos; otherwise a
  seeded simple random sample of 150. Each video's probability = p_cell × n/N (p_cell < 1 only in
  day-sampled cells). Analyses use inverse-probability weights.
- **Freeze** happens only when all channel cells are searched, metadata is complete and no manual
  review is pending. The sorted sampled ids are SHA-256 hashed and time-stamped in
  `data/interim/youtube_frame/frozen/` and `metadata/youtube_frame_freeze_log.csv` (git-tracked, so
  commits add an external timestamp).
- **Comments** are fetched only for frozen ids: all top-level comments (`commentThreads.list`,
  order=time, plain text); replies are not fetched but `reply_count` is kept. Commenter identities
  are dropped or hashed at ingest (D017).
- Any analytical ceiling on comments is applied after raw collection, with a fixed seed.

## 7. Pre-collection estimates

| item | estimate |
|---|---|
| Cells | 252 = 7 countries × 4 periods × 9 channels; 159 searchable, 93 channel-not-on-YouTube |
| Search requests | floor 159 (1 page per cell); expected ~350–500 (dense CHN cells switch to 24-day samples ≈ 25 requests each; VNM/IDN 2–3 pages; small countries 1 page) |
| `search.list` units | ~35,000–50,000 |
| `videos.list` units | ~150–500 (50 ids per unit) |
| `commentThreads.list` units | ≤ 4,200 sampled videos (28 country-periods × 150); ~2–4 pages each → ~8,000–15,000 |
| Total | ~45,000–65,000 units |
| Days | search-bound: 350–500 requests ÷ 75/day ≈ **5–7 days**; comments fit in the remaining ~2,000 units/day and one or two extra days |

## 8. Where quota could run away (and the guard)

| Risk | Guard |
|---|---|
| China: Korean news posts China-related videos daily, so a 12-month cell can exceed 2,000 videos | Dense-cell rule: a 24-day probability sample, capped at about 25 requests per cell |
| Viral videos with 10k+ comments (100+ units each) | Budget check before each video; resumable next day; no volume-based selection |
| Expired page tokens on multi-day cells | Fall back to the date cursor (same query) |
| Relevance of search results | Rules plus manual review; the universe is kept in full |

## 9. Known limitations

- `search.list` recall is incomplete (an index, not an archive); deleted and private videos are absent.
- Channel entry changes the channel mix across periods for the 2010–11 events. Early windows rest on
  MBC, MBN, JTBC, TV Chosun and Channel A. Report channel-balanced subsets (channels present in all
  four periods of a case) as a robustness check; windows are not shifted to favourable periods.
- IDN's post-event window contains its 2021 down-classification.
- Title-based relevance undercounts videos that discuss a country without naming it in the title.
