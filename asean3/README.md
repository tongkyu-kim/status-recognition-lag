# ASEAN+3 industrial homogeneity and status differentiation (pilot, in progress)

Separate study inside the status-recognition-lag repository. Scripts live in `asean3/scripts/`.
Raw files go through the parent's write-once helper into `data/raw/<source_id>/<date>/`. Derived
data (`asean3/data/`) and outputs (`asean3/outputs/`) are git-ignored and rebuilt by the scripts.
Dropbox syncs them between machines.

## Status at handoff (2026-10-14)

| Step | Script | State |
|---|---|---|
| Atlas extra pulls (all-country HS92 L4 for PRODY; 91 ASEAN+3 bilateral totals) | `a01_acq_atlas_extra.py` | **Done** (654 CPY files + pairs, `data/raw/complexity_atlas/2026-10-14`) |
| UNGD statements 2009–2024 (gadebate.un.org, sessions 64–79) | `a02_acq_ungd.py` | **Done**. Inventory: `asean3/data/interim/ungd_inventory.csv`. Not parsed yet. |
| Japanese Diet speeches: target alias × {産業, 競争, 技術, 追い上げ, 追い抜}, 2000–2024 | `a03_acq_jp_diet.py` | **Partial.** Stopped at about CHN 2008. Resumable: rerun it and existing files are skipped. |
| ASEAN Plus Three statements (asean.org sitemaps) | `a04_acq_asean.py` | **Partial.** Stopped while asean.org returned HTTP 429. Resumable. |
| Economic panel (ESI and decompositions, PRODY, RCA overlap, dependence, relative capability, geography/history) | `b01_build_econ_panel.py` | **Built.** `asean3/data/processed/esi_pair_year.parquet` (91 pairs; HS92 1995–2024, SITC 1962–2024) and `dyad_year.parquet` (182 directed dyads × 1995–2024 = 5,460 rows). Checks: `asean3/outputs/diagnostics/econ_panel_checks.csv`. |

Hand-coded inputs to verify: `asean3/config/dyad_geo_history.csv` (capital distance, land contiguity,
shared colonizer, territorial/maritime disputes 2000–2024) and `asean3/config/directed_hierarchy.csv`
(Japanese colonial rule of Korea and wartime occupation, recorded in both directions).

## Findings so far

- **WTO TPR is blocked for automated retrieval.** docs.wto.org robots.txt disallows all agents.
  www.wto.org disallows generic agents and answers Claude agents with HTTP 402 (pay-per-crawl). The
  Japanese MOFA and Geneva-mission sites return Akamai "Access Denied". So WTO Gate 1 needs a manual
  deposit: download the TPR minutes (WT/TPR/M/<n>, plus Add.1 for the written Q&A) for ASEAN+3
  reviews from 2000 to 2024 in a browser, and put them in `data/raw/wto_tpr/<date>/`.
- **UNGD 2000–2008 is not on gadebate** (sessions 55–63 return 404), and documents.un.org disallows
  /doc and /api. The UNGDC (Harvard Dataverse doi:10.7910/DVN/0TJX8Y, CC0, 1946–2025) has a
  guestbook, so it needs a manual download.
- **ESI sanity checks.** HS92 ESI correlates 0.98 with SITC ESI. Spearman(PCI 1995–99, PRODY
  1995–99) = 0.80, so the two measures are related but not interchangeable. The decomposition
  residual (up to 6.3 ESI points) is the Atlas "unspecified" product, which has no PCI. Example
  levels: JPN–KOR 46.8 (1995) → 60.6 (2024); CHN–VNM 26.2 → 54.1, with the high-PCI contribution
  rising from 1.0 to 24.5; KOR–VNM 10.9 → 32.2.
- Diet API caveats: matching is by substring. タイ needs the particle-bound forms used in the
  script and a regex filter downstream. 中国 also matches 中国地方 (a Japanese region) and needs
  filtering.
- No ANTHROPIC_API_KEY on the first machine, so LLM coding was planned in-session. Per parent
  decision D012, any LLM coding needs a pinned model, a versioned prompt, stored raw outputs and
  human validation.

## Next steps

1. Rerun `a03` and `a04` until complete.
2. Parse UNGD PDFs and Diet records (filter false matches), then build observation opportunities
   with explicit denominators.
3. Rule-based baseline plus LLM coding pilot. Unvalidated until humans code a sample.
4. Gate 4 descriptive and exploratory models (Japan observer → 13 targets), then the feasibility
   report at `asean3/outputs/reports/asean3_status_research_feasibility.md`.
