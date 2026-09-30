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
