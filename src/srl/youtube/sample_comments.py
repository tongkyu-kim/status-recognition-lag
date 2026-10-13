"""Comment corpora A-D and the stratified human-coding sample (deterministic seeds).

A_full                  all comments (descriptive volume)
B_equal_video           <= N random top-level comments per video (replies excluded)
C_equal_country_year    <= M random comments per country-year drawn from B
D_high_engagement       top-K comments by likes per video (robustness only)
coding sample           stratified by country x year-bin x frame x engagement-bin

Duplicates/spam (srl.youtube.deduplicate) and non-Korean comments are excluded from B-D and the
coding sample; exclusions are counted in the sampling log.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from srl.utils.config import load_config


def _eligible(comments: pd.DataFrame) -> pd.DataFrame:
    ok = comments["is_korean"].astype(bool)
    for col in ("dup_within_video", "dup_same_author_cross_video", "too_short"):
        if col in comments:
            ok &= ~comments[col].astype(bool)
    return comments[ok]


def _cap_group(df: pd.DataFrame, by: list[str], n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    keys = df[by].astype(str).agg("|".join, axis=1)
    order = pd.Series(rng.random(len(df)), index=df.index)
    ranked = order.groupby(keys).rank(method="first")
    return df[ranked <= n]


def attach_country(comments: pd.DataFrame, videos: pd.DataFrame) -> pd.DataFrame:
    """Primary country of a video = the country of its best-ranked query hit (ties -> alphabetical).
    Multi-country videos are flagged so they can be excluded in robustness checks."""
    first = videos[["video_id", "countries", "video_frame", "families"]].copy()
    first["country"] = first["countries"].fillna("").str.split("|").str[0]
    first["multi_country"] = first["countries"].fillna("").str.contains(r"\|")
    return comments.merge(
        first[["video_id", "country", "multi_country", "video_frame", "families"]], on="video_id", how="left"
    )


def build_corpora(
    comments: pd.DataFrame, videos: pd.DataFrame
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    cfg = load_config("youtube_sampling")
    seed = int(cfg["seed"])
    cc = cfg["corpora"]
    base = attach_country(comments, videos)
    elig = _eligible(base)
    top = elig[~elig["is_reply"].astype(bool)]
    corpora = {"A_full": base}
    corpora["B_equal_video"] = _cap_group(
        top, ["video_id"], int(cc["B_equal_video"]["max_top_level_per_video"]), seed
    )
    corpora["C_equal_country_year"] = _cap_group(
        corpora["B_equal_video"],
        ["country", "year"],
        int(cc["C_equal_country_year"]["max_per_country_year"]),
        seed + 1,
    )
    k = int(cc["D_high_engagement"]["top_k_per_video"])
    corpora["D_high_engagement"] = (
        top.sort_values(["video_id", "like_count"], ascending=[True, False]).groupby("video_id").head(k)
    )
    log = pd.DataFrame(
        [
            {
                "corpus": name,
                "n_comments": len(df),
                "n_videos": df["video_id"].nunique(),
                "rule": str(cc.get(name, {}).get("description", "all comments")),
                "seed": seed,
                "excluded_non_korean_or_dup": len(base) - len(elig),
            }
            for name, df in corpora.items()
        ]
    )
    return corpora, log


def coding_sample(
    comments: pd.DataFrame, videos: pd.DataFrame, n_per_country: int | None = None
) -> pd.DataFrame:
    cfg = load_config("youtube_sampling")
    cs, seed = cfg["coding_sample"], int(cfg["seed"])
    n_per_country = n_per_country or int(cs["pilot_n_per_major_case"])
    df = _eligible(attach_country(comments, videos))
    df = df[~df["is_reply"].astype(bool)].copy()
    if df.empty:
        return df
    bins = cs["year_bins"]
    df["year_bin"] = pd.cut(
        df["year"], [b[0] - 0.5 for b in bins] + [bins[-1][1] + 0.5], labels=[f"{a}-{b}" for a, b in bins]
    )
    q = float(cs["engagement_quantile"])
    thr = df.groupby("video_id")["like_count"].transform(lambda s: s.quantile(q))
    df["engagement_bin"] = np.where(df["like_count"] >= thr, "high", "low")
    df["frame_stratum"] = df["video_frame"].fillna(df["families"].fillna("unknown").str.split("|").str[0])
    rng = np.random.default_rng(seed + 7)
    out = []
    for country, g in df.groupby("country"):
        strata = g.groupby(["year_bin", "frame_stratum", "engagement_bin"], observed=True)
        per = max(1, n_per_country // max(strata.ngroups, 1))
        picked = (
            strata.apply(
                lambda s, per=per: s.sample(min(len(s), per), random_state=int(rng.integers(1e9))),
                include_groups=False,
            )
            .reset_index(level=[0, 1, 2])
            .reset_index(drop=True)
        )
        picked["country"] = country
        out.append(picked.head(n_per_country))
    return pd.concat(out, ignore_index=True) if out else df.head(0)
