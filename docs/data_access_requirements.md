# Data access requirements (status, 2026-10-13)

Per the overhaul brief Section VII.17-18: distinguishes downloaded/verified, available-not-
downloaded, requires-credentials, requires-institutional-access, requires-manual-annotation, and
unavailable/unverified. Every row below reflects an actual check performed in this pass (web
search; see citations), not an assumption.

## A. Downloaded and verified (already in this repository, reused from the legacy project)

| Source | Coverage | Status |
|---|---|---|
| World Bank WDI | GDPpc, productivity, MVA, patents, R&D, 1960-2025, USA/JPN/KOR/CHN + 9 others | in `data/interim/prelim/macro_country_year.csv` |
| Atlas of Economic Complexity | SITC L4 1962-2024, HS92 L4 1995-2024, USA/JPN/KOR/CHN | raw JSON in `data/raw/complexity_atlas/`; used directly for `data/processed/industrial_crossover_candidates.csv` |
| Korean government text (MOFA, MOTIE, Presidential Office, korea.kr) | ~91k documents, Korean language, mentions of China and 11 ASEAN states including Vietnam | `data/interim/prelim/gov_documents_korea.csv` + text parquet |
| UN Comtrade totals | Korea bilateral trade, 1988-2025 | `data/interim/prelim/trade_country_year.csv` |

## B. Available, not yet downloaded (no credential needed)

| Source | What it adds | Access mechanics (verified) |
|---|---|---|
| CEPII BACI | HS6-digit bilateral trade, 1995-2024, 200 countries, Etalab Open Licence (no registration) | Direct ZIP download per HS revision at cepii.fr/DATA_DOWNLOAD/baci/; would sharpen the semiconductor/display/battery crossover analysis beyond the current HS4 resolution |
| World Values Survey | Cross-national attitude items, multiple waves | Free download after registration at worldvaluessurvey.org; non-commercial reuse permitted with citation, no redistribution |
| Pew Research Center Global Attitudes | Favorability toward China/Japan/Korea by country, 2002-2025 | Published annual PDF reports confirmed (e.g. pg_2025.07.15_global-views-china-2025_report.pdf: Japan's favorable view of China = 13% in 2025; Korea's fell 25%->19%, 2024->2025); a raw-microdata download page likely exists under pewresearch.org/global but was NOT confirmed in this pass -- needs a direct check of that page |
| MHLW (Japan) vital statistics, international marriages by nationality | Japan-Korea marriage counts by direction, with a direct English PDF table | mhlw.go.jp/english/database/db-hw/dl/vs06_3_Marriages_by_nationalities_of_partners.pdf; historical peak 44,701 (2006, all nationalities), Korean nationals ~25.7% of foreign grooms of Japanese brides in 2016 |
| Statistics Korea, international marriages | Korea-Japan marriage counts by direction, recent years | Not downloaded directly; verified via Korea Times/Seoul Economic Daily reporting of Statistics Korea (KOSIS) figures: Korean-groom/Japanese-bride marriages 599 (2022) -> 840 (2023) -> 1,176 (2024, +40%); reverse direction ~147 (2024), about 1/5 of a decade earlier. Raw KOSIS table not yet pulled. |

## C. Requires credentials (API key or registration beyond free account)

| Source | Needed | Status |
|---|---|---|
| UN Comtrade keyed API (HS6, uncapped) | API key (task M1 in the legacy project's manual_data_tasks.md) | unchanged from legacy status |
| OECD TiVA | not yet searched in this pass | unresolved |
| WIPO patent statistics / IP5 statistics | not yet searched in this pass | unresolved |

## D. Requires institutional access or manual export (no automated path found)

| Source | Why | Status |
|---|---|---|
| EAI/Genron Korea-Japan Joint Perception Survey | Annual reports published (genron-npo.net/en/opinion_polls/, eai.or.kr/press_poll.php) with comparative data tables by year, but a bulk machine-readable microdata export was not confirmed in this pass -- the English reports appear to be PDF/HTML, not CSV/SPSS files. Already used in peer-reviewed work (kim2025geopolitics) so the underlying data exists; access mechanics for raw response-level data need a direct inquiry to EAI or Genron NPO. | manual verification needed (task S1, proposed) |
| Asan Institute "South Koreans and Their Neighbors" (2025) | Found during search (asaninst.org); favorability score 4.52/10 reported, record high | same as above -- report found, microdata access not checked |
| Historical Japanese press archives (Asahi, Nikkei) | Likely paywalled/institutional-subscription; not checked against any specific institutional access this project has | not checked -- brief explicitly instructs not to bypass paywalls |

## E. Requires manual annotation (by design, not a gap)

| Item | Per brief section |
|---|---|
| 400-600 item multilingual human-coded recognition validation sample | III.6 -- coding interface not yet built in this pass |
| Y2/Y3 YouTube frame coding (legacy, unchanged status) | carried over from legacy `docs/youtube_manual_tasks.md` |

## F. Not yet searched (explicitly open, not claimed as unavailable)

- Japanese-side government/media text corpus (MOFA Japan, Diet record full text beyond the
  existing `jp_diet` yearly mention-count series, major Japanese newspapers) -- this is the single
  largest gap for the jpn_kor case, since without it the project cannot measure how Japan's own
  institutions describe Korea (only how Korea describes itself and others is currently collected).
- Chinese-language sources, if the kor_chn case needs China's own self-positioning text (the brief
  Section III.6 lists Chinese as a "where necessary" language).
- OECD TiVA, WIPO patent/IP5 statistics (noted above).
- Any sector-specific industry data source (DisplaySearch/Omdia/IHS Markit, Clarksons shipping
  statistics) needed to replace the unreliable HS9013 display proxy -- see `config/sectors.yaml`.

## Priority ranking for manual action (most consequential first)

1. **Japanese-side media/government text corpus** -- without this, the jpn_kor case cannot test
   the core question (whether Japan's recognition of Korea lags) at all; everything else in this
   report is secondary to this gap.
2. **EAI/Genron microdata access inquiry** -- the single most directly usable, already-precedented
   survey source; worth a direct email/registration attempt before assuming it is unavailable.
3. **CEPII BACI download** -- free, no credential, immediately actionable, sharpens the existing
   crossover analysis.
4. **Pew Global Attitudes raw microdata page check** -- low-cost to verify, high value if available.
5. **OECD TiVA / WIPO access check** -- not yet attempted.
