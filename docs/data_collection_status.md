# Data collection status

Autonomous collection run of **2026-09-30**. Numbers were refreshed at the end of the run (see
"Snapshot" at the bottom). Machine-readable companions:

| File | Content |
|---|---|
| `metadata/source_catalog.csv` | One row per source: status, access, licence, coverage, raw-file counts |
| `metadata/download_summary.csv` | Requests, outcomes and MB per source |
| `outputs/diagnostics/coverage_table.csv` | Source × construct coverage |
| `outputs/diagnostics/qc_summary.csv` | Quality checks |

Manual work: [manual_data_tasks.md](manual_data_tasks.md). Sources and terms:
[data_sources.md](data_sources.md). Decisions made during collection: D015–D021 in
[decisions.md](decisions.md). YouTube: [youtube_collection_status.md](youtube_collection_status.md).

## 1. Successfully collected

| Source | Files (raw) | Years | Countries | Variables | Quality status |
|---|---|---|---|---|---|
| World Bank WDI (`wb_wdi`) | 29 indicator JSON + metadata | 1960–2025 | panel + HKG, MAC, JPN, USA, WLD | GDP, GDPpc (current / constant / PPP), GNIpc Atlas, population, GDP per worker, MVA level and share, industry share, high-tech exports, manufactures share, merchandise trade, trade/GDP, FDI in/outflows, patents (resident / non-resident), R&D, researchers | No duplicates. Balanced for all 13: GDPpc 1990–2025, GDP per worker 1991–2025, MVA 2010–2024 only, high-tech exports 2020–2023 only. MMR/TLS lack patents. |
| WB income classifications (`wb_income_class`) | OGHIST.xlsx, CLASS.xlsx, FY26 + FY27 official notes (PDF), live API snapshot | FY1989–FY2027 | all economies | income group by fiscal year, thresholds | Verified. 92% agree with groups recomputed from today's GNI; the gaps are data revisions (D016). |
| Atlas of Economic Complexity (`complexity_atlas`) | ~260 JSON | HS92 1995–2024; SITC 1962–2024 | panel + JPN, USA; ECI for all | ECI, COI, PCI (HS4), country × HS4 exports / imports / RCA / market share, Korea × partner HS4 flows | Sound. ECI ranks here include small economies. The API gives no ranking-eligibility flag, so TLS/BRN ECI (e.g. TLS rank 2 in 1995) is unreliable. |
| OECD FDI by counterpart (`oecd_fdi`) | 4 CSV (139 MB) | BMD3 ~1985–2013; BMD4 2005– | reporters KOR, JPN, USA × panel counterparts | flows, positions, income; inward/outward | Retrieved; not yet cleaned. Confidential cells suppressed by reporters. |
| UNCTADstat FDI (`unctad`) | 1 bulk file (.7z) | 1970– | all | aggregate FDI flows and stocks | Aggregate only. |
| Korea Eximbank ODI reports (`fdi_korea`) | 78 HWPX/DOCX (75 distinct releases, 2008Q2–2026Q2) from data.go.kr dataset 3040164 | reports 2008–2026; parsed annual series 2015–2025 | major destinations: VNM, CHN, SGP, IDN (+HKG), with MYS, MMR, KHM, THA, PHL in some years | gross ODI (US$ million) by destination, region and industry | Annual values match report text (e.g. VNM 2025 = 2,945). Revisions across reports flagged. 2008–2014 not yet parsed (narrative format). |
| Event sources (`event_sources`) | WTO member pages (13), UN LDC list PDF, Korea FTA portal pages | 1995–2029 | panel | WTO accession, LDC inclusion and graduation schedule, FTA entry into force | All 13 WTO dates and 7 FTA dates verified. `wto_country_LAO.html` is a soft 404 kept for provenance. |
| MOFA web archive (`kr_mofa`) | list, search and document HTML; white-paper PDFs | 2000–2026 (Korean press releases) | — | 13 boards: KO press releases (22,741), explanatory releases, briefings (2,382), speeches (825), op-eds / interviews (3,801), summit pages 2025–26, work plans; EN press releases (11,354), briefings (1,738), speeches (1,004) | Inventory complete. Full text: see snapshot. |
| MOTIR web archive (`kr_motie`) | list, search and document HTML | 2014–2026 as dated; legacy releases back to the 1990s | — | press releases (30,092), explanatory releases (2,630) | **18,703 legacy releases carry the migration date 2016-12-09** (see §2). |
| Presidential speeches (`kr_presidential_office`) | Excel export, list and document HTML, Office JSON | inventory 1948–2025; texts 1988–2025 | — | title, date, president, type, venue, source, text | Texts for 노태우 → 윤석열 (6,338 targeted); current Office from 2025-06. |
| korea.kr trade/industry lineage (`kr_policy_briefing`) | lists 2008–2014, 158 document pages, 316 attachments | 2008–2014 | — | titles, dates, ministry label at the time (산업자원부 → 지식경제부 → 산업통상자원부); HWP text | HWP extraction works on 316/316 attachments. |
| Japan Diet API counts (`jp_diet`) | 124 JSON | 1980–2010 | — | yearly speeches mentioning 韓国 (+経済, +追い上げ, +競争) | 665–1,596 Korea-mentioning speeches per year; "Korea + competition" rises from ~20 to ~104 per year. |

## 2. Partially collected

| Source | Exact gap | How to close it |
|---|---|---|
| UN Comtrade (`un_comtrade`) | The totals matrix (13 × 14 × X/M, 1988–2025) is complete. HS2 Korea ↔ partner dyads were collected in quota-limited batches; any dyad-years missing at the end are listed in the snapshot. No HS4/HS6 world-export files (preview caps 500 records per call). | Rerun `acq_comtrade.py` (resumable); keyed API (M1) for HS6 |
| MOTIR legacy releases | 17,744 legacy releases need their pages fetched to recover original dates and text; the fetch runs at ~1 page / 1.2 s (resumable: `acq_kr_motie.py --phases legacy`). Until then those documents have `date_reliable = False` and no year. | Let the job finish; rebuild `gov_documents_korea.csv` |
| MOTIR full text | HTML bodies of post-2014 releases are summaries; full text sits in PDF/HWP attachments, which were not downloaded. Mention counts are lower bounds. | V3, then C4 |
| MOFA full text | Large boards: full text only for documents the site's own search returns for a partner alias (D021). Recall has not been measured yet. | Sample non-hit documents; extend if recall is low |
| korea.kr 2008–2014 | Text only for 158 title hits; the other 4,830 releases are inventory-only (bodies are stubs, text is in HWP). | Bulk HWP download (≈5k files) if the pre-2014 MOTIE series is needed beyond the legacy MOTIR batch |
| UNCTAD | Aggregate only; bilateral tables are on unctad.org (403) | M4 |
| Partner-state text (`partner_gov_text`) | Feasibility samples only (§6) | §6 recommendations |

## 3. Failed automated retrieval

| Target | Why | Handling |
|---|---|---|
| World Bank data-catalog API | Persistent HTTP 429 (rate limit) | Used direct file URLs and official PDFs |
| Harvard Dataverse bulk files (Atlas HS6) | Guestbook form (terms/identity step), not bypassed | M3 |
| UN Comtrade full detail | Preview quota (403 "Out of call volume quota") and 500-record cap | Waited per Retry-After; M1 for the keyed API |
| unctad.org | HTTP 403 to automated clients | M4 |
| National Assembly API | Keyless calls capped at 5 rows; `likms.assembly.go.kr/record/` disallowed by robots.txt | M6 |
| Japan MOFA Bluebooks, METI 通商白書 | HTTP 403 | M9 |
| Indonesia presidenri.go.id | Cloudflare challenge | M8 |
| Cambodia mfaic.gov.kh | "Request Rejected" | M8 |
| Viet Nam mofa.gov.vn (English) | 404 | M8; en.baochinhphu.vn works instead |
| OECD TiVA | Dataflows located; the structure endpoint did not return dimensions in this session | C3 (automatable next step) |
| YouTube Data API | No API key | Y1 |
| Korea Eximbank full country table (small partners, pre-2015 country detail) | Interactive portal | M4 (narrowed; the data.go.kr reports are collected) |
| KCS, WIPO detail | Interactive portals or key required | M2, M5 |

## 4. Manual action required

See [manual_data_tasks.md](manual_data_tasks.md): 21 tasks. **Class A (must be done by a
human):** Y1 YouTube API key, M1 Comtrade key, M3 Atlas Dataverse files, M4 Korean ODI + UNCTAD
bilateral FDI, M6 National Assembly key, M7 pre-2025 Presidential Office archives, M8 blocked
partner sites, M2 KCS key, M5 WIPO, M9 Japanese white papers. **Class B:** V1 partnership dates,
V2 alias precision, V3 MOTIR attachments, V4 trade breaks, V5 MOFA completeness, Y2/Y3 YouTube
coding. **Class C:** C2 BACI, C3 TiVA, C4 MOTIR attachments, Y4 transcripts.

## 5. Formal status transitions (event-study inputs)

`data/interim/prelim/event_transitions.csv` (61 events; `verification` column):

- **World Bank income transitions (verified, official files).** Effective 1 July of the
  announcement year (FY = year + 1):
  - VNM L→LM 2010 (FY11), LM→UM 2026 (FY27)
  - CHN LM→UM 2011 (FY12); earlier L↔LM switching 1998–2000
  - LAO L→LM 2011 (FY12)
  - THA LM→UM 2011 (FY12)
  - KHM L→LM 2016 (FY17)
  - MMR L→LM 2015 (FY16)
  - TLS L→LM 2008 (FY09)
  - IDN →LM 1994, back to L 1999, →LM 2004, →UM 2020 (FY21), →LM 2021 (FY22), →UM 2023 (FY24)
  - PHL LM→UM 2026 (FY27)
  - MYS LM→UM 1993 (FY94)
  - KOR UM→H 1996, H→UM 1999, UM→H 2002

  All candidate dates in the brief are confirmed. VNM and PHL have a new UM transition in July
  2026, which is too recent for a post-period.
- **LDC:** KHM (1991), LAO (1971), MMR (1987) and TLS (2003) are LDCs. LAO graduation is scheduled for
  **24 Nov 2026** (A/RES/76/8) and KHM for **19 Dec 2029** (A/RES/79/230).
- **WTO membership (verified):** BRN, IDN, KOR, MYS, MMR, PHL, SGP, THA 1995-01-01; KHM 2004-10-13;
  CHN 2001-12-11; VNM 2007-01-11; LAO 2013-02-02; TLS 2024-08-30.
- **Korea FTAs in force (verified, fta.motir.go.kr):** SGP 2006-03-02; ASEAN (goods) 2007-06-01;
  CHN and VNM 2015-12-20; KHM 2022-12-01; IDN CEPA 2023-01-01; SGP DPA 2023-01-14; PHL 2024-12-31.
  MYS signed/concluded; THA under negotiation.
- **Strategic-partnership upgrades and TLS's ASEAN accession:** listed as `candidate_unverified`
  (task V1). `outputs/diagnostics/partnership_evidence.csv` lists the earliest government documents
  using each partnership-tier phrase, to help verification.

**Viability.** Staggered income-class transitions (VNM 2010, CHN/LAO/THA 2011, MMR 2015, KHM 2016,
IDN 2020–23) give an event-study design with several treated units and never- or late-treated
comparisons (PHL until 2026, MYS/BRN/SGP no change in window). With 12 partners, inference needs
small-cluster methods (wild cluster bootstrap / randomization inference). FTA dates cluster (CHN
and VNM on the same day), so they are better used as controls or a separate event type. The design
is **viable as a descriptive/event-time analysis**; causal claims need the pre-trend and
anticipation checks already specified in `docs/research_design.md`.

## 6. Partner-state status claims (feasibility)

| State | Official source tested | Archive / date coverage | Language | Accessibility | Automated retrieval realistic? | Manual needed? |
|---|---|---|---|---|---|---|
| China | MFA English: Speeches (`/eng/xw/zyjh/`), Spokesperson's Remarks; State Council English | Speeches list page 60 reaches 2016; deeper pages likely go further | English (and Chinese) | Open, robots OK, static HTML | **Yes** | No |
| Viet Nam | Government portal en.baochinhphu.vn: `/speeches.htm`, `/j-statements.htm` | First page OK; pagination scheme not discovered (page-30 URL 404) | English | Open | Probably (pagination to be worked out) | MOFA English site 404 (M8) |
| Cambodia | Press OCM English: speech, press-release and news categories | Speech category page 50 reaches 2023 | English (Khmer primary) | Open (WordPress-style) | **Yes** | MFAIC blocks ("Request Rejected") → M8 |
| Indonesia | Cabinet Secretariat English: Speech Transcript category | Page 100 reaches 2022–23 | English | Open (WordPress) | **Yes** | presidenri.go.id behind Cloudflare → M8 |
| Singapore | PMO newsroom (one page lists all items), MFA newsroom | Long history (single 5.9 MB listing) | English | Open | **Yes** | No |

**Verdict:** claimed-status coding (construct G) is feasible in English for CHN, SGP, IDN and KHM.
VNM is likely feasible via the government portal. Full collection is a separate, scoped task.

## 7. Historical comparison feasibility

| Case | Source | Access | Batch download | Machine-readable | Sample saved |
|---|---|---|---|---|---|
| Japan → Korea | Diet Record API (kokkai.ndl.go.jp) | Open API, no key | Yes | Yes (JSON, speaker, party, committee) | Yes: yearly counts 1980–2010 |
| Japan → Korea | MOFA Diplomatic Bluebooks | HTTP 403 | Manual (M9) | HTML/PDF | No |
| Japan → Korea | METI 通商白書 | HTTP 403 | Manual (M9) | PDF | No |
| Japan → Korea | Objective status | WDI (JPN, KOR 1960–), Atlas SITC ECI 1962– | Done | Yes | Yes |
| US → Japan | FRUS (TEI XML on GitHub, HistoryAtState/frus) | Public domain | Yes (git clone, several GB) | Yes (TEI) | Repo metadata only |
| US → Japan | Public Papers of the Presidents (govinfo) | Pages reachable; API needs an api.data.gov key | Partly | PDF/XML | Landing page |
| US → Japan | Objective status | WDI, Atlas SITC 1962– (USA, JPN) | Done | Yes | Yes |

Japan → Korea can reuse the same constructs: parliamentary attention from the Diet API (open),
status from WDI/Atlas, and executive texts pending M9. US → Japan is feasible from FRUS plus the
public papers.

## 8. Answers to the research-priority questions

1. **Objective-status proximity series?** Yes, annually, for all 13 countries: GDPpc (current,
   constant, PPP) 1990–2025, GDP per worker 1991–2025, ECI 1995–2024 (SITC back to 1964, with
   caution for small economies). MVA is balanced only from 2010. High-tech export share needs to be
   rebuilt from Atlas HS4 with a product list (WDI is balanced only 2020–23). Preview:
   `outputs/diagnostics/proximity_feasibility_PREVIEW.csv`. VNM (PPP GDPpc ratio 0.16 → 0.26;
   ECI rank 181 → 69) and CHN (0.14 → 0.43; rank 62 → 15) converge strongly, while THA/MYS drift
   away: useful variation.
2. **Industrial / export similarity over time?** Yes at HS4, 1995–2024 (Atlas country × product
   exports for all 13 plus world product totals). HS6 needs M1/M3/C2.
3. **Korean bilateral economic salience?** Yes: Korea-reported bilateral trade 1988–2025 with
   Korea- and partner-side shares, plus FDI positions and flows by counterpart (OECD).
4. **Korean government corpus large enough?** Yes. About 91k documents are inventoried across
   MOFA, MOTIR, korea.kr and the Presidential Archives, with full text for all speeches and for
   partner-hit releases (snapshot below). Caveats: MOTIR legacy dates (being repaired), MOTIR
   summaries vs attachments, and search-based full-text selection (D021).
5. **Formal transitions for event study / DiD?** Yes (§5).
6. **VNM, CHN, LAO, KHM, SGP, THA, IDN comparable?** On macro, trade, complexity and events, yes.
   LAO has sparse mirror trade and no reliable early ECI rank. Government-text volume differs
   greatly (CHN ≫ VNM > IDN, SGP > THA, KHM > LAO; see `gov_corpus_coverage.csv`), so
   attention needs share-based measures.
7. **Replicable for Japan → Korea?** Partly now (Diet API, WDI, Atlas SITC). Executive texts need
   M9.

## 9. Recommended next steps (ranked by research value)

1. **Finish the running collectors and rebuild:** MOTIR legacy pages (date repair + text), MOFA
   full text, presidential texts, Comtrade HS2. Then run `build_gov_documents.py`,
   `build_prelim.py`, `quality_checks.py`, `build_catalog.py` and
   `python tasks.py register-raw`.
2. **V1:** verify partnership-upgrade dates from joint statements (the event-study backbone).
3. **V2 + recall check:** validate alias precision (KWIC) and estimate search recall on a random
   sample of non-hit MOFA documents (D021).
4. **Y1 + YouTube pilot (2 days)**, then Y2 coding of 100–200 comments per major case, then the
   stop-condition checklist.
5. **HS4 overlap measures:** build Finger–Kreinin / cosine similarity and RCA overlap from
   `trade_product_country_year.parquet`, plus a high-tech share from an HS4 product list.
6. **M1 (Comtrade key)** or **C2 (BACI)** for HS6 similarity and a complete HS2 dyad panel.
7. **FDI salience:** harmonize Korea Eximbank report series (2015–2025, `odi_korea_country_year.csv`)
   with OECD BMD3/BMD4 by counterpart; parse the 2008–2014 reports; M4 for LAO/BRN/TLS.
8. **V3 → C4:** decide on MOTIR attachment harvesting for full-text attention.
9. **Partner claimed-status corpus:** CHN MFA speeches, SGP PMO, IDN Setkab, KHM Press OCM (all
   automatable); VNM portal pagination.
10. **C3 TiVA** (GVC exposure) and **M6** National Assembly (legislative attention, analysed
    separately).

## Snapshot (end of run)

_Generated 2026-10-12T13:36 (Korea time) by `scripts/acquire/write_snapshot.py`._

### Korean government corpus

| source_id | documents | full_text | first_year | last_year | mention_any_partner |
|---|---|---|---|---|---|
| kr_mofa | 44260 | 15860 | 1996.0 | 2026.0 | 14300 |
| kr_motie | 32722 | 17999 | 1989.0 | 2026.0 | 2944 |
| kr_policy_briefing | 4988 | 158 | 2008.0 | 2014.0 | 169 |
| kr_presidential_office | 10331 | 7401 | 1948.0 | 2026.0 | 1770 |

MOTIR dates (legacy releases imported with 2016-12-09 are repaired where evidence exists; `date_reliable` flags the rest):

| MOTIR date source | documents |
|---|---|
| original_date | 23813 |
| korea_kr_exact_title | 4062 |
| body_explicit_date | 2260 |
| body_weekday_era | 1252 |
| body_release_date | 757 |
| title_year_only | 578 |

### Preliminary derived files

| file | rows |
|---|---|
| data/interim/prelim/macro_country_year.csv | 1188 |
| data/interim/prelim/income_classification_country_year.csv | 8697 |
| data/interim/prelim/trade_country_year.csv | 456 |
| data/interim/prelim/trade_product_country_year.csv | 445687 |
| data/interim/prelim/event_transitions.csv | 61 |
| data/interim/prelim/odi_korea_country_year.csv | 74 |

### Quality checks (`outputs/diagnostics/qc_summary.csv`)

| check | count |
|---|---|
| macro duplicate country-year rows | 0 |
| macro \|dlog\|>0.5 year-on-year jumps (inspect) | 140 |
| WDI PPP series base year (see names) | 3 |
| negative trade values | 0 |
| trade duplicate partner-year rows | 0 |
| trade hs_revision_kor | 72 |
| trade hs_revision_partner | 68 |
| trade flag_mirror_gap_gt25pct | 106 |
| trade flag_trade_break_dlog_gt_0_7 | 19 |
| trade flag_missing_kor_reported | 30 |
| trade flag_missing_mirror | 123 |
| Comtrade reporters with >1 numeric code over time | 0 |
| dataset country names not normalizable (excl. aggregates; see file) | 2 |
| income class != recomputed from current GNI vintage (revisions; expected) | 36 |
| gov documents: duplicate doc_id | 0 |
| gov documents: cross-source duplicates (title+date) | 4361 |
| gov documents: missing date | 10491 |

### YouTube sampling frame (daily task `SRL YouTube frame daily`)

```text
Status at 2026-10-06T17:16:41 (Korea time)
search cells still open: 0
videos awaiting metadata: 0
frozen country x period samples: 11 / 28
sampled videos still needing comments: 0

WAITING ON YOU: 946 videos need manual review (data/processed/youtube_frame/video_manual_review.csv).
Put decisions in data/raw/human_coding/<YYYY-MM-DD>/youtube_frame_review.csv
with columns video_id,country,decision,reason,reviewer (decision = include | exclude).
By country x period: CHN_P3=7, CHN_P4=93, IDN_P1=274, IDN_P2=74, IDN_P3=104, IDN_P4=109, KHM_P1=19, KHM_P2=25, KHM_P3=11, KHM_P4=13, LAO_P4=14, MMR_P1=6, MMR_P2=45, MMR_P3=49, MMR_P4=98, THA_P3=1, THA_P4=4
```
