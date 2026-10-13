# Manual data tasks

Generated from `metadata/manual_actions.yaml` by `scripts/acquire/build_catalog.py` - edit the
YAML, not this file. After any download, put the files in a **new dated folder** under the
destination and run `python tasks.py register-raw` (checksums into `data/raw_manifest.csv`).
Credentials go only into the git-ignored `.env` at the repository root.

| id | class | priority | source |
|---|---|---|---|
| [M1](#m1) | A | HIGH | UN Comtrade (full API, free registration) |
| [M3](#m3) | A | MEDIUM | Harvard Growth Lab - International Trade Data (HS92) on Harvard Dataverse |
| [M4](#m4) | A | MEDIUM | Korean outward FDI - small partners / full country table (Korea Eximbank) and UNCTAD bilateral FDI |
| [M6](#m6) | A | MEDIUM | National Assembly Open API (열린국회정보) |
| [M7](#m7) | A | MEDIUM | Presidential Office web archives (Moon, Yoon administrations) - Presidential Archives web archive |
| [M8](#m8) | A | MEDIUM | Partner governments blocking automation |
| [W1](#w1) | A | MEDIUM | Korean Diplomatic White Papers 1990-2025 - OCR of scanned editions (LibreOffice part DONE 2026-10-02) |
| [M2](#m2) | A | LOW | Korea Customs Service trade statistics (data.go.kr API) |
| [M5](#m5) | A | LOW | WIPO IP Statistics Data Center |
| [M9](#m9) | A | LOW | Japan MOFA Diplomatic Bluebooks; METI White Papers (通商白書) |
| [Y1](#y1) | A | DONE | YouTube Data API v3 (Google Cloud) - DONE 2026-09-30 (key in .env; regenerate after pilot, it was pasted in chat) |
| [V1](#v1) | B | HIGH | Strategic-partnership upgrades (Korea x partner) |
| [V2](#v2) | B | HIGH | Country alias precision (text matching) |
| [Y2](#y2) | B | HIGH | YouTube pilot manual inspection (after Y1) |
| [V3](#v3) | B | MEDIUM | MOTIE/MOTIR attention measurement |
| [V4](#v4) | B | MEDIUM | Trade series breaks |
| [V5](#v5) | B | MEDIUM | MOFA archive completeness |
| [Y3](#y3) | B | MEDIUM | YouTube video frames (after Y1) |
| [C2](#c2) | C | MEDIUM | BACI (CEPII) HS92 / HS17 |
| [C4](#c4) | C | MEDIUM | MOTIR press-release attachments (full text) |
| [C3](#c3) | C | LOW | GVC / TiVA |
| [Y4](#y4) | C | LOW | YouTube transcripts |

## A. Must be done manually

### M1

- **Source:** UN Comtrade (full API, free registration)
- **Priority:** HIGH
- **URL / navigation:** https://comtradedeveloper.un.org/
- **What to do:** Register (free) at comtradeplus.un.org, subscribe to the "comtrade - v1" free product in the developer portal, copy the primary key into .env as COMTRADE_API_KEY=<key>. The keyed API allows up to 250,000 records per call, which makes HS6 world-export files for the 13 panel countries (needed for HS6 export similarity) feasible. Tell Claude/the pipeline to switch scripts/acquire/acq_comtrade.py to the keyed endpoint (https://comtradeapi.un.org/data/v1/get/C/A/HS).
- **File(s):** none (credential)
- **Preferred filename:** `.env (line COMTRADE_API_KEY=...)`
- **Destination:** `repository root (never commit)`
- **Why it is needed:** The keyless preview caps 500 records/call and throttles after ~190 calls; HS6 overlap measures need the keyed API (or BACI, task C2).

### M3

- **Source:** Harvard Growth Lab - International Trade Data (HS92) on Harvard Dataverse
- **Priority:** MEDIUM
- **URL / navigation:** https://doi.org/10.7910/DVN/T4CHWJ
- **What to do:** Open the DOI, click "Access Dataset" -> download these files individually, completing the guestbook form when asked: hs92_country_product_year_6.csv (1.0 GB), hs92_country_year.csv, hs92_product_year_6.csv, hs92_data_dictionary.csv. Optional (large): hs92_country_country_product_year_6_2010_2019.csv and _2020_2024.csv for HS6 bilateral flows. Also download growth_proj_eci_rankings.csv from doi:10.7910/DVN/XTAQMC and product_hs92.csv from doi:10.7910/DVN/3BAL1O.
- **File(s):** hs92_country_product_year_6.csv (+ listed files)
- **Preferred filename:** `keep original names`
- **Destination:** `data/raw/complexity_atlas_dataverse/<YYYY-MM-DD>/`
- **Why it is needed:** HS6 country-product exports for export-similarity robustness; the API was used for HS4 only. The guestbook form is a terms/identity step we do not bypass.

### M4

- **Source:** Korean outward FDI - small partners / full country table (Korea Eximbank) and UNCTAD bilateral FDI
- **Priority:** MEDIUM
- **URL / navigation:** https://stats.koreaexim.go.kr/
- **What to do:** PARTLY DONE: the quarterly reports on data.go.kr (dataset 3040164, pointed out by the PI) were downloaded automatically and parsed for 2015-2025 (major destinations only). Remaining: (a) Korea Eximbank: 해외투자통계 -> 국가별 -> select all years (1980-latest), all countries, amounts on both 신고(declared) and 투자(invested) basis -> export Excel. Repeat for 국가별 x 업종별 if available. (b) UNCTAD Bilateral FDI Statistics 2014 (covers 2001-2012): https://unctad.org/topic/investment/investment-statistics-and-trends -> "Bilateral FDI statistics" -> download the Excel files for Korea, China, Viet Nam, Indonesia, Thailand, Malaysia, Philippines, Singapore, Cambodia, Lao PDR, Myanmar, Brunei (keep the file names as listed on the page).
- **File(s):** Excel exports
- **Preferred filename:** `koreaexim_odi_by_country_<years>.xlsx; UNCTAD files keep original names`
- **Destination:** `data/raw/fdi_korea/<YYYY-MM-DD>/ and data/raw/unctad_bilateral/<YYYY-MM-DD>/`
- **Why it is needed:** OECD BMD4 by counterpart starts ~2005 and has suppressed cells; Korean-reported ODI goes back to 1980. unctad.org returns HTTP 403 to automated clients.

### M6

- **Source:** National Assembly Open API (열린국회정보)
- **Priority:** MEDIUM
- **URL / navigation:** https://open.assembly.go.kr/portal/openapi/main.do
- **What to do:** Log in / register -> 마이페이지 -> 인증키 발급 (free). Store as ASSEMBLY_API_KEY=<key> in .env. Relevant services: 위원회 회의록 (https://open.assembly.go.kr/portal/data/service/selectAPIServicePage.do/OR137O001023MZ19321) and 본회의 회의록 (also on data.go.kr: https://www.data.go.kr/data/15126007/openapi.do). Check in the service page whether full text or only PDF links are returned before scaling.
- **File(s):** none (credential)
- **Preferred filename:** `.env (line ASSEMBLY_API_KEY=...)`
- **Destination:** `repository root`
- **Why it is needed:** Keyless calls return at most 5 rows; likms.assembly.go.kr/record/ is disallowed by robots.txt.

### M7

- **Source:** Presidential Office web archives (Moon, Yoon administrations) - Presidential Archives web archive
- **Priority:** MEDIUM
- **URL / navigation:** https://www.pa.go.kr/
- **What to do:** On pa.go.kr use 대통령기록 -> 웹기록 (archived Cheong Wa Dae / Office websites). For 2017-2025, locate the briefing boards (브리핑, 대변인 브리핑, 정상회담 결과) and check whether pages can be saved as HTML. If a list is only browsable interactively, save the list pages (Ctrl+S) per year.
- **File(s):** saved HTML pages
- **Preferred filename:** `office_<admin>_<board>_pNNN.html`
- **Destination:** `data/raw/kr_presidential_office/<YYYY-MM-DD>/office_archive/`
- **Why it is needed:** Speech texts are covered (pa.go.kr speech DB), but Office briefings/summit readouts before 2025 are not.

### M8

- **Source:** Partner governments blocking automation
- **Priority:** MEDIUM
- **URL / navigation:** https://www.presidenri.go.id/ ; https://www.mfaic.gov.kh/ ; https://mofa.gov.vn/
- **What to do:** presidenri.go.id (Indonesia, Cloudflare challenge), mfaic.gov.kh (Cambodia, 'Request Rejected'), mofa.gov.vn English (404 at retrieval) cannot be collected automatically. For the feasibility sample, open each site in a browser, find the speeches / press-release section, and save 5-10 English-language items per year for 2015, 2020, 2025 (Save Page As -> HTML complete).
- **File(s):** saved HTML
- **Preferred filename:** `<ISO>_<site>_<YYYY-MM-DD>_<slug>.html`
- **Destination:** `data/raw/partner_gov_text/<YYYY-MM-DD>/manual/`
- **Why it is needed:** Needed to judge whether claimed-status coding (construct G) is feasible for IDN, KHM, VNM.

### W1

- **Source:** Korean Diplomatic White Papers 1990-2025 - OCR of scanned editions (LibreOffice part DONE 2026-10-02)
- **Priority:** MEDIUM
- **URL / navigation:** data/interim/text/white_papers_index.csv (status per file); raw PDFs in data/raw/kr_mofa/2026-09-30/white_papers/
- **What to do:** Text corpus built for 183 files (1998-2008, 2011-2017, 2019, 2021-2025; LibreOffice converted old HWP/.doc). Remaining: 105 image-only PDFs (status needs_ocr) for 1990-1997, 2009, 2010, 2018, 2020, plus 6 zip members from 1999-2000 that failed conversion. Either approve installing Tesseract OCR with Korean data (winget UB-Mannheim.TesseractOCR + kor.traineddata) so Claude can OCR them, or OCR them yourself (e.g. Acrobat "Recognize text") and save OCR'd copies as NEW files.
- **File(s):** OCR'd PDFs or text (never overwrite the originals)
- **Preferred filename:** `wp_<seq>_<file_seq>_ocr.pdf or .txt`
- **Destination:** `data/raw/kr_mofa_white_papers_ocr/<YYYY-MM-DD>/`
- **Why it is needed:** Completes the only official ANNUAL text series back to 1990 (pre-1998 editions are all scans).

### M2

- **Source:** Korea Customs Service trade statistics (data.go.kr API)
- **Priority:** LOW
- **URL / navigation:** https://www.data.go.kr/
- **What to do:** Log in to data.go.kr -> search "관세청 국가별 수출입실적" / "관세청 품목별 국가별 수출입실적" -> 활용신청 (apply) -> store the service key as KCS_API_KEY=<key> in .env. Only needed for monthly or HSK 10-digit Korean data. (Dataset ids were not verified here - pick the 관세청 provider entries.)
- **File(s):** none (credential)
- **Preferred filename:** `.env`
- **Destination:** `repository root`
- **Why it is needed:** Monthly Korea-partner trade (optional; annual Comtrade/Atlas suffice for the panel).

### M5

- **Source:** WIPO IP Statistics Data Center
- **Priority:** LOW
- **URL / navigation:** https://www3.wipo.int/ipstats/ips-search/
- **What to do:** Indicator "Patent applications" -> Report type "Total count by applicant's origin" (and "Resident applications per country of origin") -> select the 13 panel countries (+JPN, USA) -> years 1980-latest -> Export CSV. Repeat for "PCT international applications by origin" and, optionally, "Patent applications by technology field" (35 WIPO fields).
- **File(s):** CSV exports
- **Preferred filename:** `wipo_<indicator>_<report>.csv`
- **Destination:** `data/raw/wipo/<YYYY-MM-DD>/`
- **Why it is needed:** WDI already holds resident/non-resident applications (WIPO-sourced); PCT and technology fields add capability detail.

### M9

- **Source:** Japan MOFA Diplomatic Bluebooks; METI White Papers (通商白書)
- **Priority:** LOW
- **URL / navigation:** https://www.mofa.go.jp/mofaj/gaiko/bluebook/index.html ; https://www.meti.go.jp/report/gaisei/index.html
- **What to do:** Both return HTTP 403 to automated clients. In a browser, download the Korea sections (朝鮮半島 / 韓国) of the Diplomatic Bluebook for 1985, 1990, 1995, 2000, 2005, 2010 and the 通商白書 chapters on Asian/NIEs competition for the same years (PDF).
- **File(s):** PDFs
- **Preferred filename:** `jp_bluebook_<year>_<section>.pdf ; jp_tsuhaku_<year>_<chapter>.pdf`
- **Destination:** `data/raw/jp_mofa_bluebook/<YYYY-MM-DD>/ ; data/raw/jp_meti_whitepaper/<YYYY-MM-DD>/`
- **Why it is needed:** Japan -> Korea extension (only if that case is taken up).

### Y1

- **Source:** YouTube Data API v3 (Google Cloud) - DONE 2026-09-30 (key in .env; regenerate after pilot, it was pasted in chat)
- **Priority:** DONE
- **URL / navigation:** https://console.cloud.google.com/apis/library/youtube.googleapis.com
- **What to do:** Sign in to Google Cloud -> create (or pick) a project -> APIs & Services -> Library -> enable "YouTube Data API v3" -> Credentials -> Create credentials -> API key -> restrict the key to the YouTube Data API v3. Put it in a file named .env at the repository root (git-ignored) as YOUTUBE_API_KEY=<key>. Then run: python scripts/youtube/run_youtube.py plan search --pilot --run <YYYY-MM-DD> (day 1) and: python scripts/youtube/run_youtube.py videos channels comments build sample --pilot --run <same date> (day 2).
- **File(s):** none (credential)
- **Preferred filename:** `.env (line YOUTUBE_API_KEY=...)`
- **Destination:** `repository root (never commit)`
- **Why it is needed:** The YouTube public-recognition pilot cannot run without a key; no HTML scraping is permitted.


## B. Recommended manual validation

### V1

- **Source:** Strategic-partnership upgrades (Korea x partner)
- **Priority:** HIGH
- **URL / navigation:** https://www.mofa.go.kr/www/brd/m_4080/list.do
- **What to do:** data/interim/prelim/event_transitions.csv rows with verification=candidate_unverified list candidate upgrades (e.g. VNM 2009/2022, IDN 2006/2017, CHN 2008, ASEAN CSP 2024, KHM/PHL 2024). For each, find the joint statement in the MOFA corpus (data/interim/prelim/gov_documents_korea.csv, search the title for 공동성명 / 공동선언 + country) and record the exact date and wording.
- **File(s):** none
- **Preferred filename:** `edit event_transitions verification via a new events_manual.csv`
- **Destination:** `data/external/events_manual.csv`
- **Why it is needed:** Partnership upgrades are key events for the event-study design; dates must come from official texts.

### V2

- **Source:** Country alias precision (text matching)
- **Priority:** HIGH
- **URL / navigation:** outputs/diagnostics/gov_mention_surface_counts.csv
- **What to do:** Review keyword-in-context samples for ambiguous aliases (인니, 버마, 월남, 'Lao', 'Burma', 'PRC', 한·중 compounds; 중국 inside 남중국해 is shielded). Record false-positive rates.
- **File(s):** none
- **Preferred filename:** `docs/decisions.md entry`
- **Destination:** `docs/decisions.md`
- **Why it is needed:** Attention measures depend on mention counts (D009).

### Y2

- **Source:** YouTube pilot manual inspection (after Y1)
- **Priority:** HIGH
- **URL / navigation:** data/interim/coding_samples/youtube_comment_coding_sheet.csv
- **What to do:** Code 100-200 comments per major pilot case (VNM, CHN; then KHM, SGP) with docs/youtube_coding_protocol.md; two coders on a 50-comment overlap; compute Krippendorff's alpha.
- **File(s):** coding sheet
- **Preferred filename:** `youtube_comment_coding_<coder>_<date>.csv`
- **Destination:** `data/raw/human_coding/<YYYY-MM-DD>/`
- **Why it is needed:** Stop condition 3 (recognition vs dismissal codable reliably) can only be tested by humans.

### V3

- **Source:** MOTIE/MOTIR attention measurement
- **Priority:** MEDIUM
- **URL / navigation:** https://www.motir.go.kr/kor/article/ATCL3f49a5a8c
- **What to do:** Compare 50 random MOTIR releases' HTML summary vs. PDF attachment: how often is a partner mentioned in the attachment but not in the summary? Decide whether bulk attachment download (~30k PDFs, ~9 GB) is needed (task C4).
- **File(s):** none
- **Preferred filename:** `n/a`
- **Destination:** `docs/decisions.md`
- **Why it is needed:** MOTIR HTML bodies are summaries; country mentions are under-counted.

### V4

- **Source:** Trade series breaks
- **Priority:** MEDIUM
- **URL / navigation:** outputs/diagnostics/trade_quality.csv
- **What to do:** Inspect flagged mirror gaps and HS revision years (H0->H1 1996, H2 2002, H3 2007, H4 2012, H5 2017, H6 2022) for suspicious jumps, esp. LAO, MMR, KHM, TLS (sparse reporting).
- **File(s):** none
- **Preferred filename:** `n/a`
- **Destination:** `docs/decisions.md`
- **Why it is needed:** Interdependence measures should not reflect reporting changes.

### V5

- **Source:** MOFA archive completeness
- **Priority:** MEDIUM
- **URL / navigation:** https://www.mofa.go.kr/www/brd/m_4080/list.do
- **What to do:** The Korean press-release board starts 2000-01; check whether 1998-1999 (MOFAT) releases exist elsewhere (e.g. archived site via 국가기록원 웹기록 or the Presidential Archives) and whether yearly counts in outputs/diagnostics/gov_corpus_coverage.csv show migration gaps.
- **File(s):** none
- **Preferred filename:** `n/a`
- **Destination:** `docs/decisions.md`
- **Why it is needed:** Attention denominators require a complete inventory.

### Y3

- **Source:** YouTube video frames (after Y1)
- **Priority:** MEDIUM
- **URL / navigation:** data/interim/coding_samples/youtube_video_coding_sheet.csv
- **What to do:** Code video_frame for all pilot videos from title + description (+ transcript if obtained, Y4).
- **File(s):** coding sheet
- **Preferred filename:** `youtube_video_coding_<coder>_<date>.csv`
- **Destination:** `data/raw/human_coding/<YYYY-MM-DD>/`
- **Why it is needed:** Frames are the stimulus variable for H-P3 to H-P5.


## C. Optional enhancements

### C2

- **Source:** BACI (CEPII) HS92 / HS17
- **Priority:** MEDIUM
- **URL / navigation:** https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37
- **What to do:** Download BACI_HS92_V<latest>.zip (~2+ GB) from the CEPII page, check the licence text on the page, and store OUTSIDE Dropbox if space is a concern (set SRL_PROJECT_ROOT or symlink data/raw/baci).
- **File(s):** BACI_HS92_V<version>.zip
- **Preferred filename:** `original`
- **Destination:** `data/raw/baci/<YYYY-MM-DD>/`
- **Why it is needed:** Reconciled HS6 bilateral flows for all countries (RCA/similarity at HS6).

### C4

- **Source:** MOTIR press-release attachments (full text)
- **Priority:** MEDIUM
- **URL / navigation:** https://www.motir.go.kr/kor/article/ATCL3f49a5a8c
- **What to do:** Automatable but large (~30k PDF/HWP, ~9 GB); decide after V3 and storage check.
- **File(s):** attachments
- **Preferred filename:** `<seq>_<n>.<ext>`
- **Destination:** `data/raw/kr_motie/<YYYY-MM-DD>/attachments/`
- **Why it is needed:** Full-text attention measures for the trade/industry ministry.

### C3

- **Source:** GVC / TiVA
- **Priority:** LOW
- **URL / navigation:** https://sdmx.oecd.org/public/rest/dataflow/OECD.STI.PIE/DSD_TIVA_MAINLV@DF_MAINLV
- **What to do:** Automatable (public SDMX); scheduled as a next step rather than manual.
- **File(s):** n/a
- **Preferred filename:** `n/a`
- **Destination:** `data/raw/oecd_tiva/<YYYY-MM-DD>/`
- **Why it is needed:** Value-added exposure measures (interdependence).

### Y4

- **Source:** YouTube transcripts
- **Priority:** LOW
- **URL / navigation:** https://www.youtube.com/
- **What to do:** The official API cannot return caption text for third-party videos. For a small subset of pilot videos whose frame is ambiguous, open the video, use "Show transcript", and copy the text into <video_id>.txt.
- **File(s):** text files
- **Preferred filename:** `<video_id>.txt`
- **Destination:** `data/raw/youtube_transcripts_manual/<YYYY-MM-DD>/`
- **Why it is needed:** Frame coding "not from title alone"; transcripts help only for ambiguous cases.
