"""PILOT stage 2: partner-year panel and exploratory tests of H1-H5 (docs/research_design.md).

EXPLORATORY. Recognition comes from an unvalidated candidate dictionary applied to Korean
government text only (no YouTube, no human coding); 12 partner clusters; several choices below
(phase cut-offs, sentence filter, competitive sub-frames) were made for this pilot and are NOT
pre-registered. Read results as feasibility and direction-of-travel evidence, not as tests.

Inputs : data/interim/pilot/partner_sentences.parquet (scripts/pilot/build_frames.py)
         data/interim/prelim/{macro_country_year,trade_country_year,gov_documents_korea}.csv
         data/interim/prelim/trade_product_country_year.parquet, config/youtube_frame.yaml (events)
Outputs: data/interim/pilot/panel_partner_year.csv
         outputs/pilot/{hypothesis_tests,event_study,phase_summary,coverage}.csv + fig_*.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from srl.status.proximity import relative_to_reference  # noqa: E402
from srl.trade.overlap import export_similarity_index  # noqa: E402
from srl.utils.config import get_path  # noqa: E402

PARTNERS = ["BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "TLS", "VNM", "CHN"]
EVENTS = {"VNM": 2010, "CHN": 2011, "LAO": 2011, "THA": 2011, "MMR": 2015, "KHM": 2016, "IDN": 2020}
Y0, Y1 = 1998, 2024
MIN_FRAMED = 3  # partner-years need >= 3 framed (H or V) sentences for the recognition logit
RNG = np.random.default_rng(20260930)
B = 1999
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
COMPETITIVE_CORE = ("competitive__competitor", "competitive__catch_up_threat")
OUT = get_path("outputs.diagnostics").parent / "pilot"


# --------------------------------------------------------------------------- measures
def recognition_measures() -> pd.DataFrame:
    s = pd.read_parquet(get_path("data.interim") / "pilot" / "partner_sentences.parquet")
    s = s[(s["n_partners_in_sentence"] <= 2) & s["year"].between(Y0, Y1)].copy()
    sub = s["subframes"].fillna("")
    s["H"] = s["frame_horizontal"] > 0
    s["V"] = s["frame_vertical"] > 0
    s["C"] = sub.str.contains("|".join(COMPETITIVE_CORE), regex=True)
    s["T"] = s["text"].str.contains(r"덤핑|dumping|세이프가드|safeguard|수입규제", case=False, regex=True)
    g = s.groupby(["partner", "year"]).agg(n_sent=("text", "size"), nH=("H", "sum"), nV=("V", "sum"),
                                           nC=("C", "sum"), nT=("T", "sum")).reset_index()
    g = g.rename(columns={"partner": "iso3"})
    g["year"] = g["year"].astype(int)
    framed = g["nH"] + g["nV"]
    g["recog_logit"] = np.where(framed >= MIN_FRAMED, np.log((g["nH"] + 0.5) / (g["nV"] + 0.5)), np.nan)
    g["recog_share"] = np.where(framed >= MIN_FRAMED, g["nH"] / framed.where(framed > 0), np.nan)
    g["h_rate"] = 1000 * g["nH"] / g["n_sent"]
    g["v_rate"] = 1000 * g["nV"] / g["n_sent"]
    g["comp_rate"] = 1000 * g["nC"] / g["n_sent"]
    g["friction_rate"] = 1000 * g["nT"] / g["n_sent"]
    return g


def attention_measures() -> pd.DataFrame:
    cols = ["source_id", "board", "language", "year", "date_reliable", "is_cross_source_duplicate"]
    g = pd.read_csv(get_path("data.interim") / "prelim" / "gov_documents_korea.csv", low_memory=False,
                    usecols=cols + [f"mentions_{c}" for c in PARTNERS])
    g = g[g["year"].notna() & (g["date_reliable"].astype(str) != "False")
          & ~g["is_cross_source_duplicate"].astype(bool) & (g["language"] == "ko")]
    g["year"] = g["year"].astype(int)
    out = []
    for name, sel in {"att_mofa": (g["source_id"] == "kr_mofa") & (g["board"] == "보도자료"),
                      "att_pres": g["source_id"] == "kr_presidential_office",
                      "att_all": pd.Series(True, index=g.index)}.items():
        d = g[sel]
        n = d.groupby("year").size()
        for c in PARTNERS:
            k = (d[f"mentions_{c}"] > 0).groupby(d["year"]).sum()
            out.append(pd.DataFrame({"iso3": c, "year": n.index, "measure": name,
                                     "value": np.log((k.reindex(n.index, fill_value=0) + 0.5)
                                                     / (n - k.reindex(n.index, fill_value=0) + 0.5)),
                                     "n_docs": n.to_numpy()}))
    a = pd.concat(out)
    a = a[(a["measure"] != "att_mofa") | (a["year"] >= 2000)]  # MOFA ko inventory complete from 2000
    return a.pivot_table(index=["iso3", "year"], columns="measure", values="value").reset_index()


def status_measures() -> pd.DataFrame:
    pre = get_path("data.interim") / "prelim"
    m = pd.read_csv(pre / "macro_country_year.csv")
    m = m[m["iso3"].isin(PARTNERS + ["KOR"])].copy()
    m["prox_gdp"] = relative_to_reference(m, "gdppc_ppp_const", method="log_ratio")
    m["prox_eci"] = relative_to_reference(m, "eci_hs92", method="gap")
    m["gdp_ratio"] = np.exp(m["prox_gdp"])
    prod = pd.read_parquet(pre / "trade_product_country_year.parquet", columns=["iso3", "year", "hs92_4",
                                                                                 "export_value"])
    prod = prod.rename(columns={"hs92_4": "product", "export_value": "value"})
    esi = export_similarity_index(prod[prod["value"] > 0])
    t = pd.read_csv(pre / "trade_country_year.csv").rename(columns={"partner": "iso3"})
    st = m[["iso3", "year", "prox_gdp", "prox_eci", "gdp_ratio"]].merge(esi, on=["iso3", "year"], how="left")
    st = st.merge(t[["iso3", "year", "share_kor_trade"]], on=["iso3", "year"], how="left")
    st["log_trade_share"] = np.log(st["share_kor_trade"].where(st["share_kor_trade"] > 0))
    return st[st["iso3"].isin(PARTNERS)]


def build_panel() -> pd.DataFrame:
    grid = pd.MultiIndex.from_product([PARTNERS, range(Y0, Y1 + 1)], names=["iso3", "year"]).to_frame(index=False)
    p = grid.merge(status_measures(), on=["iso3", "year"], how="left")
    p = p.merge(recognition_measures(), on=["iso3", "year"], how="left")
    p = p.merge(attention_measures(), on=["iso3", "year"], how="left")
    for c in ("n_sent", "nH", "nV", "nC", "nT"):
        p[c] = p[c].fillna(0).astype(int)
    p = p.sort_values(["iso3", "year"])
    for c in ("log_trade_share", "prox_gdp", "esi"):
        p[f"{c}_l1"] = p.groupby("iso3")[c].shift(1)
    z = lambda s: (s - s.mean()) / s.std()  # noqa: E731
    p["prox_comp"] = (z(p["prox_gdp"]) + z(p["prox_eci"])) / 2
    p["event_year"] = p["iso3"].map(EVENTS)
    # phases on the GDPpc PPP ratio to Korea (pilot cut-offs, not pre-registered)
    p["phase"] = pd.cut(p["gdp_ratio"], [0, 0.2, 0.4, 0.7, np.inf], labels=["far", "approach", "near", "at/above"])
    hi = (p["gdp_ratio"] >= 0.4).astype(int)
    run = hi.groupby((hi != hi.shift()).cumsum()).cumsum() * hi
    p["sustained_high"] = (run.groupby(p["iso3"]).transform(lambda r: r) >= 5).astype(int)
    return p


# --------------------------------------------------------------------------- estimation
def _design(d: pd.DataFrame, xs: list[str], fe: tuple[str, ...]) -> np.ndarray:
    parts = [d[xs].to_numpy(float), np.ones((len(d), 1))]
    for f in fe:
        parts.append(pd.get_dummies(d[f], drop_first=True, dtype=float).to_numpy())
    return np.column_stack(parts)


def _ols_cr1(y, X, groups):
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ y
    u = y - X @ b
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(groups):
        sg = X[groups == g].T @ u[groups == g]
        meat += np.outer(sg, sg)
    n, k, G = len(y), np.linalg.matrix_rank(X), len(np.unique(groups))
    V = XtX_inv @ meat @ XtX_inv * G / (G - 1) * (n - 1) / (n - k)
    return b, np.sqrt(np.clip(np.diag(V), 0, None)), u


def fe_ols(d: pd.DataFrame, y: str, xs: list[str], test: list[str], fe=("iso3", "year")) -> list[dict]:
    d = d.dropna(subset=[y, *xs]).reset_index(drop=True)
    groups = d["iso3"].to_numpy()
    G = len(np.unique(groups))
    X = _design(d, xs, fe)
    yv = d[y].to_numpy(float)
    b, se, _ = _ols_cr1(yv, X, groups)
    webb = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
    out = []
    for term in test:
        j = xs.index(term)
        t_obs = b[j] / se[j]
        # wild cluster restricted bootstrap (Webb weights), null b_j = 0 imposed
        Xr = np.delete(X, j, axis=1)
        br = np.linalg.pinv(Xr.T @ Xr) @ Xr.T @ yv
        fit_r, u_r = Xr @ br, yv - Xr @ br
        gid = pd.factorize(groups)[0]
        t_star = np.empty(B)
        for r in range(B):
            w = RNG.choice(webb, size=G)[gid]
            bs, ses, _ = _ols_cr1(fit_r + u_r * w, X, groups)
            t_star[r] = bs[j] / ses[j] if ses[j] > 0 else 0.0
        out.append({"term": term, "coef": b[j], "se_cr1": se[j], "t": t_obs,
                    "p_cr1": 2 * stats.t.sf(abs(t_obs), G - 1), "p_wcb": float(np.mean(np.abs(t_star) >= abs(t_obs))),
                    "ci_lo": b[j] - stats.t.ppf(0.975, G - 1) * se[j], "ci_hi": b[j] + stats.t.ppf(0.975, G - 1) * se[j],
                    "n_obs": len(d), "n_clusters": G, "fe": "+".join(fe), "outcome": y})
    return out


def centered(p: pd.DataFrame, a: str, m: str) -> pd.DataFrame:
    p = p.copy()
    p[f"{a}_c"] = p[a] - p[a].mean()
    p[f"{m}_c"] = p[m] - p[m].mean()
    p[f"{a}_x_{m}"] = p[f"{a}_c"] * p[f"{m}_c"]
    return p


def run_tests(p: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(h, spec, expected, res, sample="all"):
        for r in res:
            rows.append({"hypothesis": h, "spec": spec, "sample": sample, "expected_sign": expected, **r})

    small = ~p["iso3"].isin(["BRN", "SGP", "TLS"])
    # H1: lagged economic salience -> attention, within partner over time
    for att in ("att_mofa", "att_pres", "att_all"):
        add("H1", f"{att} ~ log_trade_share_l1 + prox_gdp_l1 | partner+year", "+",
            fe_ols(p, att, ["log_trade_share_l1", "prox_gdp_l1"], ["log_trade_share_l1"]))
    # attention vs recognition are distinct: does salience also move recognition?
    add("H1-distinct", "recog_logit ~ log_trade_share_l1 + prox_gdp | partner+year", "0 (distinct)",
        fe_ols(p, "recog_logit", ["log_trade_share_l1", "prox_gdp"], ["log_trade_share_l1"]))
    # H2: recognition vs proximity -- slope and curvature (within and between)
    for prox in ("prox_gdp", "prox_eci", "prox_comp"):
        q = p.assign(**{f"{prox}_sq": (p[prox] - p[prox].mean()) ** 2})
        add("H2", f"recog_logit ~ {prox} + {prox}^2 | partner+year", "+ / - (concave)",
            fe_ols(q, "recog_logit", [prox, f"{prox}_sq"], [prox, f"{prox}_sq"]))
        add("H2", f"recog_logit ~ {prox} + {prox}^2 | year (between+within)", "+ / - (concave)",
            fe_ols(q, "recog_logit", [prox, f"{prox}_sq"], [prox, f"{prox}_sq"], fe=("year",)))
    add("H2", "recog_logit ~ prox_gdp | partner+year (excl. BRN SGP TLS)", "+",
        fe_ols(p[small], "recog_logit", ["prox_gdp"], ["prox_gdp"]), sample="excl_BRN_SGP_TLS")
    for o in ("h_rate", "v_rate"):
        add("H2-components", f"{o} ~ prox_gdp | partner+year", "+ for h, - for v",
            fe_ols(p, o, ["prox_gdp"], ["prox_gdp"]))
    # H3 / H4: the slope shortfall is larger at high overlap / dependence (negative interaction)
    q = centered(p, "prox_gdp", "esi")
    add("H3", "recog_logit ~ prox_gdp_c * esi_c | partner+year", "- (interaction)",
        fe_ols(q, "recog_logit", ["prox_gdp_c", "esi_c", "prox_gdp_x_esi"], ["prox_gdp_x_esi", "esi_c"]))
    add("H3-competitive", "comp_rate ~ esi + prox_gdp | partner+year", "+ (esi)",
        fe_ols(p, "comp_rate", ["esi", "prox_gdp"], ["esi"]))
    q = centered(p, "prox_gdp", "log_trade_share")
    add("H4", "recog_logit ~ prox_gdp_c * log_trade_share_c | partner+year", "- (interaction)",
        fe_ols(q, "recog_logit", ["prox_gdp_c", "log_trade_share_c", "prox_gdp_x_log_trade_share"],
               ["prox_gdp_x_log_trade_share", "log_trade_share_c"]))
    # H5: after sustained high capability recognition catches up; competitive framing may stay high
    add("H5", "recog_logit ~ prox_gdp + sustained_high | partner+year", "+",
        fe_ols(p, "recog_logit", ["prox_gdp", "sustained_high"], ["sustained_high"]))
    add("H5-competitive", "comp_rate ~ prox_gdp + sustained_high | partner+year", "+ or 0",
        fe_ols(p, "comp_rate", ["prox_gdp", "sustained_high"], ["sustained_high"]))
    return pd.DataFrame(rows)


def event_study(p: pd.DataFrame) -> pd.DataFrame:
    bins = [(-99, -5), (-4, -4), (-3, -3), (-2, -2), (0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 99)]
    q = p.copy()
    k = q["year"] - q["event_year"]
    names = []
    for lo, hi in bins:
        n = f"k_{lo}" if lo == hi else (f"k_le{hi}" if lo < -50 else f"k_ge{lo}")
        q[n] = (k.between(lo, hi)).astype(float).fillna(0)
        names.append(n)
    rows = []
    for y in ("prox_gdp", "att_mofa", "recog_logit", "comp_rate"):
        for r in fe_ols(q, y, names, names):
            rows.append(r)
    es = pd.DataFrame(rows)
    es["k"] = es["term"].map(lambda t: int(t.replace("k_le", "").replace("k_ge", "").replace("k_", "")))
    ref = es[["outcome"]].drop_duplicates().assign(k=-1, coef=0.0, ci_lo=0.0, ci_hi=0.0, term="k_-1 (ref)")
    return pd.concat([es, ref]).sort_values(["outcome", "k"])


# --------------------------------------------------------------------------- figures
def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.axhline(0, color=INK2, linewidth=0.8)


def fig_event_study(es: pd.DataFrame) -> None:
    labels = {"prox_gdp": "Objective proximity\n(log GDPpc PPP ratio to KOR)",
              "att_mofa": "Attention\n(logit share of MOFA releases)",
              "recog_logit": "Recognition\n(logit horizontal vs vertical)",
              "comp_rate": "Competitive framing\n(per 1,000 partner sentences)"}
    colors = {"prox_gdp": BLUE, "att_mofa": GREEN, "recog_logit": ORANGE, "comp_rate": "#6250d6"}
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.4), facecolor=SURFACE)
    for ax, (o, lab) in zip(axes, labels.items(), strict=True):
        d = es[es["outcome"] == o]
        ax.fill_between(d["k"], d["ci_lo"], d["ci_hi"], color=colors[o], alpha=0.15, linewidth=0)
        ax.plot(d["k"], d["coef"], color=colors[o], linewidth=2, marker="o", markersize=4)
        ax.axvline(-0.5, color=INK2, linewidth=0.8, linestyle=":")
        _style(ax)
        ax.set_title(lab, fontsize=9, color=INK, loc="left")
        ax.set_xlabel("Years from income-group upgrade (end bins pooled)", fontsize=8, color=INK2)
    fig.suptitle("Event study around first World Bank income upgrades (7 events; partner + year FE; "
                 "95% CI, 12 clusters)", fontsize=10, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_event_study.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


def fig_partner_lag(p: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 4, figsize=(13, 8), sharex=True, facecolor=SURFACE)
    for ax, c in zip(axes.flat, sorted(PARTNERS), strict=True):
        d = p[p["iso3"] == c].sort_values("year")
        zs = lambda s: (s - s.mean()) / s.std()  # noqa: E731
        ax.plot(d["year"], zs(d["prox_gdp"]), color=BLUE, linewidth=2, label="Objective proximity (z)")
        r = d["recog_logit"].rolling(3, min_periods=2, center=True).mean()
        ax.plot(d["year"], zs(r), color=ORANGE, linewidth=2, label="Recognition, 3-yr mean (z)")
        if c in EVENTS:
            ax.axvline(EVENTS[c], color=INK2, linewidth=0.8, linestyle=":")
        _style(ax)
        ax.set_title(f"{c}  (framed sentences: {int((d['nH'] + d['nV']).sum())})", fontsize=9, color=INK, loc="left")
    axes.flat[0].legend(fontsize=7, frameon=False, loc="upper left")
    fig.suptitle("Within-partner standardized proximity vs recognition (dotted line = income upgrade event)",
                 fontsize=10, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_partner_lag.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


def fig_binned(p: pd.DataFrame) -> None:
    d = p.dropna(subset=["recog_logit", "prox_gdp"]).copy()
    # within-year deviations (removes common trends in Korean government language)
    for c in ("recog_logit", "prox_gdp"):
        d[c + "_wy"] = d[c] - d.groupby("year")[c].transform("mean")
    d["bin"] = pd.qcut(d["prox_gdp"], 10, labels=False)
    b = d.groupby("bin").agg(x=("prox_gdp", "mean"), y=("recog_logit_wy", "mean"),
                             se=("recog_logit_wy", lambda s: s.std() / np.sqrt(len(s)))).reset_index()
    fig, ax = plt.subplots(figsize=(6.5, 4), facecolor=SURFACE)
    ax.scatter(d["prox_gdp"], d["recog_logit_wy"], s=10, color=GRID, edgecolor="none")
    ax.errorbar(b["x"], b["y"], yerr=1.96 * b["se"], fmt="o", color=ORANGE, markersize=6, capsize=0, linewidth=1.5)
    _style(ax)
    ax.set_xlabel("Proximity: log(partner GDPpc PPP / Korea GDPpc PPP)   (0 = parity)", fontsize=8, color=INK2)
    ax.set_ylabel("Recognition logit, deviation from year mean", fontsize=8, color=INK2)
    ax.set_title("Recognition by proximity decile (partner-years; dots grey, decile means ±95% CI)",
                 fontsize=9, color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_recognition_by_proximity.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = build_panel()
    p.to_csv(get_path("data.interim") / "pilot" / "panel_partner_year.csv", index=False)

    cov = p.groupby("iso3").agg(years=("year", "size"), sentences=("n_sent", "sum"), H=("nH", "sum"),
                                V=("nV", "sum"), C_core=("nC", "sum"), trade_friction=("nT", "sum"),
                                years_with_recog=("recog_logit", lambda s: int(s.notna().sum())),
                                gdp_ratio_first=("gdp_ratio", "first"), gdp_ratio_last=("gdp_ratio", "last"),
                                esi_first=("esi", "first"), esi_last=("esi", "last")).reset_index()
    cov.to_csv(OUT / "coverage.csv", index=False)
    print(cov.round(2).to_string())

    ph = p.groupby("phase", observed=True).agg(partner_years=("year", "size"),
                                               partners=("iso3", lambda s: ",".join(sorted(s.unique()))),
                                               recog_logit=("recog_logit", "mean"), recog_share=("recog_share", "mean"),
                                               h_rate=("h_rate", "mean"), v_rate=("v_rate", "mean"),
                                               comp_rate=("comp_rate", "mean")).reset_index()
    ph.to_csv(OUT / "phase_summary.csv", index=False)
    print(ph.round(3).to_string())

    tests = run_tests(p)
    tests.to_csv(OUT / "hypothesis_tests.csv", index=False)
    show = ["hypothesis", "spec", "term", "expected_sign", "coef", "se_cr1", "p_cr1", "p_wcb", "n_obs"]
    print(tests[show].round(3).to_string())

    es = event_study(p)
    es.to_csv(OUT / "event_study.csv", index=False)
    print(es[["outcome", "k", "coef", "ci_lo", "ci_hi", "p_wcb"]].round(3).to_string())
    fig_event_study(es)
    fig_partner_lag(p)
    fig_binned(p)


if __name__ == "__main__":
    main()
