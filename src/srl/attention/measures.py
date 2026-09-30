"""Government attention toward each partner.

Expected input: the mention table from :func:`srl.text.corpus.build_sentence_and_mention_tables`
``[sentence_id, doc_uid, source_id, date, year, entity_id, entity_type, ...]``.

Attribution rule: a sentence mentioning several partners counts once for each of them.
Measures are computed per entity and period; shares use the total over all matched *foreign*
entities in the same period (the reference state is excluded from numerator and denominator).
Which measure is primary (mentions, sentences, documents, shares, events) is an open decision.
"""

from __future__ import annotations

import pandas as pd

from srl.text.aggregation import add_period
from srl.utils.countries import group_members
from srl.utils.validation import require_columns

MENTION_REQUIRED = ["sentence_id", "doc_uid", "date", "entity_id", "entity_type"]


def _prepare(mentions: pd.DataFrame, freq: str, entity_types: tuple[str, ...],
             exclude: tuple[str, ...]) -> pd.DataFrame:
    require_columns(mentions, MENTION_REQUIRED, "mentions")
    subset = mentions[mentions["entity_type"].isin(entity_types) & ~mentions["entity_id"].isin(exclude)]
    return add_period(subset, freq=freq)


def mention_counts(mentions: pd.DataFrame, *, freq: str = "Y",
                   entity_types: tuple[str, ...] = ("country",),
                   exclude: tuple[str, ...] = ("KOR",)) -> pd.DataFrame:
    """Number of mentions per entity and period -> ``[entity_id, period, n_mentions]``."""
    df = _prepare(mentions, freq, entity_types, exclude)
    return df.groupby(["entity_id", "period"], as_index=False).size().rename(columns={"size": "n_mentions"})


def sentence_counts(mentions: pd.DataFrame, *, freq: str = "Y",
                    entity_types: tuple[str, ...] = ("country",),
                    exclude: tuple[str, ...] = ("KOR",)) -> pd.DataFrame:
    """Number of distinct sentences mentioning each entity -> ``n_sentences``."""
    df = _prepare(mentions, freq, entity_types, exclude)
    return (df.groupby(["entity_id", "period"])["sentence_id"].nunique()
              .rename("n_sentences").reset_index())


def document_counts(mentions: pd.DataFrame, *, freq: str = "Y",
                    entity_types: tuple[str, ...] = ("country",),
                    exclude: tuple[str, ...] = ("KOR",)) -> pd.DataFrame:
    """Number of distinct documents mentioning each entity -> ``n_documents``."""
    df = _prepare(mentions, freq, entity_types, exclude)
    return (df.groupby(["entity_id", "period"])["doc_uid"].nunique()
              .rename("n_documents").reset_index())


def attention_share(counts: pd.DataFrame, value_col: str) -> pd.Series:
    """Entity's share of ``value_col`` among all entities in the same period.

    Note: the denominator covers only entities present in ``counts``; to express attention as a
    share of *all* foreign-policy attention, ``counts`` must include every foreign entity (not just
    panel partners) before this function is applied.
    """
    total = counts.groupby("period")[value_col].transform("sum")
    return (counts[value_col] / total).rename(f"{value_col}_share")


def allocate_group_mentions(counts: pd.DataFrame, value_col: str, *, group: str = "ASEAN",
                            method: str = "none") -> pd.DataFrame:
    """Optionally allocate group-level counts (e.g., "ASEAN") to member states.

    ``none``: drop group rows (default; group attention analysed separately).
    ``full``: each member present in the period receives the full group count.
    ``equal_split``: each member receives count / number of members.
    Membership uses accession years from ``config/countries.yaml``; requires annual periods.
    """
    group_rows = counts[counts["entity_id"] == group]
    others = counts[counts["entity_id"] != group]
    if method == "none" or group_rows.empty:
        return others.reset_index(drop=True)
    if method not in {"full", "equal_split"}:
        raise ValueError("method must be 'none', 'full' or 'equal_split'")
    allocated = []
    for row in group_rows.itertuples(index=False):
        members = group_members(group, year=int(str(row.period)[:4]))
        value = getattr(row, value_col) / (len(members) if method == "equal_split" else 1)
        allocated += [{"entity_id": iso, "period": row.period, value_col: value} for iso in members]
    combined = pd.concat([others, pd.DataFrame(allocated)], ignore_index=True)
    return combined.groupby(["entity_id", "period"], as_index=False)[value_col].sum()


def event_counts(events: pd.DataFrame, *, freq: str = "Y") -> pd.DataFrame:
    """Count diplomatic/economic events per partner, period and type.

    Expected input ``[entity_id, date, event_type]`` (e.g., summit, ministerial_visit,
    joint_statement), hand-compiled under documented coding rules.
    Returns ``[entity_id, period, event_type, n_events]``.
    """
    require_columns(events, ["entity_id", "date", "event_type"], "events")
    df = add_period(events, freq=freq)
    return (df.groupby(["entity_id", "period", "event_type"], as_index=False).size()
              .rename(columns={"size": "n_events"}))
