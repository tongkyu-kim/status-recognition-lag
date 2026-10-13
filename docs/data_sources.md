# Data sources

The machine-readable catalog is `metadata/source_catalog.csv` / `.json`, generated from
`config/sources.yaml` by `python scripts/acquire/build_catalog.py`. This page summarizes it. What was
collected and what is missing: [data_collection_status.md](data_collection_status.md). What a human
still has to do: [manual_data_tasks.md](manual_data_tasks.md).

## Rules (D015)

- **Source hierarchy.** Tier 1 (World Bank, IMF, UN Comtrade, OECD, UNCTAD, WTO, WIPO, Korean
  ministries, Presidential Archives, National Assembly) comes first. Tier 2 (Atlas/Growth Lab,
  BACI) is used where Tier 1 lacks the series. Tier 3 (blogs, Kaggle, mirrors, Wikipedia) is used
  only to locate originals.
- **Access.** Documented APIs, public bulk endpoints, or public pages allowed by robots.txt.
  Logins, keys, CAPTCHAs, guestbook or terms forms, and HTTP 403 blocks are not bypassed; they
  become manual tasks.
- **Storage.** `data/raw/<source_id>/<YYYY-MM-DD>/`, written once (`srl.acquisition.fetch.save_raw`).
  Every request is logged in `metadata/download_log.csv`, and every raw file is checksummed in
  `data/raw_manifest.csv` (`python tasks.py register-raw`).
- **Status values:** `validated` (retrieved), `partial` (part retrieved), `manual` (needs a
  human), `candidate` (not yet checked), `rejected`.

## Sources by construct

| Construct | source_id | Status | What we have | Script |
|---|---|---|---|---|
| A objective status | `wb_wdi` | validated | 29 WDI series, panel + HKG/MAC/JPN/USA/WLD, 1960–2025 | `acq_wdi.py` |
| A / C complexity, overlap | `complexity_atlas` | validated | ECI/COI (HS92 1995–2024, SITC 1962–2024), PCI (HS4), country × HS4 exports and RCA, Korea × partner HS4 flows | `acq_atlas.py` |
| A patents | `wipo` | manual | Resident and non-resident applications via WDI; PCT and technology fields manual (M5) | — |
| C / D trade | `un_comtrade` | partial | Bilateral totals 1988–2025 (reporter + mirror); HS2 Korea ↔ partner (quota-limited) | `acq_comtrade.py` |
| C trade (HS6) | `baci` | candidate | Deferred (size); task C2 | — |
| D FDI | `oecd_fdi` | validated | FDI flows, positions and income by counterpart; reporters KOR, JPN, USA; BMD4 + BMD3 history | `acq_oecd_fdi.py` |
| D FDI | `unctad` | partial | Aggregate FDI flows and stocks (bulk); bilateral tables manual (M4) | `acq_unctad.py` |
| D FDI (Korean ODI) | `fdi_korea` | partial | Korea Eximbank quarterly/annual reports 2008–2026 (data.go.kr 3040164); parsed annual gross ODI by major destination 2015–2025 | `acq_koreaexim_odi.py`, `build_odi_reports.py` |
| E / F government text | `kr_mofa` | validated | 13 boards inventoried (2000–2026); full text for speeches, summits, work plans and alias hits; Diplomatic White Papers | `acq_kr_mofa.py` |
| E / F government text | `kr_motie` | validated | motir.go.kr press releases 2014–2026 (inventory; text for alias hits) | `acq_kr_motie.py` |
| E / F government text | `kr_policy_briefing` | partial | korea.kr trade/industry lineage 2008–2014 (inventory; HWP text for title hits) | `acq_kr_policy_briefing.py` |
| E / F government text | `kr_presidential_office` | validated | Presidential Archives speech inventory (1948–2025), texts 1988–2025; president.go.kr 2025– | `acq_kr_presidential.py` |
| E legislative text | `kr_national_assembly` | manual | Open API needs a key (M6) | — |
| G claimed status | `partner_gov_text` | partial | Feasibility samples (CHN, VNM, KHM, IDN, SGP) | ad hoc |
| H formal transitions | `wb_income_class` | validated | OGHIST FY89–FY25 + official FY26/FY27 notes | `acq_wb_income.py` |
| H formal transitions | `event_sources` | validated | WTO member pages, UN LDC list, Korea FTA portal pages | ad hoc |
| Historical (JPN → KOR) | `jp_diet` | validated | Diet API mention counts 1980–2010 | `acq_jp_diet_counts.py` |
| Historical | `jp_mofa_bluebook`, `jp_meti_whitepaper` | manual | HTTP 403 (M9) | — |
| Historical (US → JPN) | `us_frus` | validated | TEI XML repository located; not cloned | — |
| Public discourse | `youtube` | manual | Pipeline ready; API key needed (Y1) | `scripts/youtube/run_youtube.py` |

## Institutional naming (Korean government text)

| Period | Foreign ministry | Trade/industry ministry | Where the text is |
|---|---|---|---|
| 1998-02 – 2013-03 | 외교통상부 (MOFAT; incl. 통상교섭본부 trade negotiations) | 산업자원부 (MOCIE, to 2008-02), then 지식경제부 (MKE) | MOFA archive (from 2000); korea.kr (MOCIE from 2008-01 only, MKE) |
| 2013-03 – 2025 | 외교부 (MOFA) | 산업통상자원부 (MOTIE; trade negotiations moved here) | MOFA archive; motir.go.kr (from 2014-03); korea.kr 2013–14 |
| 2025 – | 외교부 | 산업통상부 (site title at retrieval; domain motir.go.kr) | MOFA archive; motir.go.kr |

Agencies are never silently merged. `institution` is the analytical grouping (MOFA / MOTIE /
President), `institution_label` preserves the name at the time, and `source_id` preserves the
archive the document came from.

## Licence summary

| Source | Terms | Redistribution in the replication package |
|---|---|---|
| World Bank WDI, income classes | CC BY 4.0 | yes, with attribution |
| Atlas (Growth Lab) | CC0 bulk files; cite Growth Lab | yes, with citation |
| UN Comtrade | UN Comtrade terms | derived data only |
| OECD | OECD terms (CC BY 4.0 for most data) | yes, with attribution |
| UNCTADstat | free use with attribution | yes |
| Korean government texts | Public-sector works; KOGL type per item | derived measures; full text only where the KOGL type allows |
| YouTube | YouTube API Services Terms | comment IDs and derived labels only |
