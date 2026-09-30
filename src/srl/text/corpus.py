"""Corpus assembly: raw deposited documents -> document, sentence and mention tables."""

from __future__ import annotations

import logging

import pandas as pd

from srl.acquisition.sources import raw_source_dir, sources_by_category
from srl.cleaning.text import normalize_text, strip_boilerplate
from srl.text.entities import EntityMatcher
from srl.text.language import detect_language
from srl.text.metadata import DOCUMENT_COLUMNS, validate_sidecar
from srl.text.segmentation import split_sentences
from srl.utils.io import sha256_file
from srl.utils.paths import relpath

logger = logging.getLogger(__name__)

SUPPORTED_TEXT_SUFFIXES = {".txt"}
SENTENCE_COLUMNS = ["sentence_id", "doc_uid", "source_id", "date", "year", "institution",
                    "doc_type", "language", "sent_idx", "text"]
MENTION_COLUMNS = ["sentence_id", "doc_uid", "source_id", "date", "year", "entity_id",
                   "entity_type", "surface", "start", "end"]


def _read_document(path) -> str:
    if path.suffix.lower() not in SUPPORTED_TEXT_SUFFIXES:
        raise NotImplementedError(
            f"No text extractor for {path.suffix} ({relpath(path)}). Choose and document an "
            "extractor (PDF/HWP/HTML) in docs/decisions.md before adding it."
        )
    return path.read_text(encoding="utf-8")


def build_document_table(categories: tuple[str, ...] = ("government_text",)) -> pd.DataFrame:
    """Read every ``metadata.csv`` sidecar under the raw folders of text sources."""
    records = []
    for category in categories:
        for source in sources_by_category(category):
            for sidecar in sorted(raw_source_dir(source.source_id).rglob("metadata.csv")):
                meta = validate_sidecar(pd.read_csv(sidecar, dtype=str), relpath(sidecar))
                for row in meta.itertuples(index=False):
                    path = sidecar.parent / row.file
                    text = strip_boilerplate(normalize_text(_read_document(path)), source.source_id)
                    language = row.language if isinstance(row.language, str) else detect_language(text)
                    records.append({
                        "doc_uid": f"{source.source_id}:{row.doc_id}",
                        "source_id": source.source_id,
                        "doc_id": row.doc_id,
                        "title": row.title,
                        "date": row.date,
                        "year": int(row.date[:4]),
                        "institution": row.institution,
                        "doc_type": row.doc_type,
                        "language": language,
                        "original_url": row.original_url,
                        "raw_path": relpath(path),
                        "sha256": sha256_file(path),
                        "n_chars": len(text),
                        "text": text,
                    })
    docs = pd.DataFrame(records, columns=DOCUMENT_COLUMNS)
    if docs["doc_uid"].duplicated().any():
        raise ValueError("Duplicate doc_uid across metadata sidecars")
    logger.info("Assembled %d documents", len(docs))
    return docs


def build_sentence_and_mention_tables(docs: pd.DataFrame, matcher: EntityMatcher, *,
                                      min_chars: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Segment documents into sentences and extract entity mentions per sentence."""
    sentences, mentions = [], []
    for doc in docs.itertuples(index=False):
        for idx, sentence in enumerate(split_sentences(doc.text, min_chars=min_chars)):
            sentence_id = f"{doc.doc_uid}:{idx}"
            base = {"sentence_id": sentence_id, "doc_uid": doc.doc_uid, "source_id": doc.source_id,
                    "date": doc.date, "year": doc.year}
            sentences.append({**base, "institution": doc.institution, "doc_type": doc.doc_type,
                              "language": doc.language, "sent_idx": idx, "text": sentence})
            for m in matcher.find(sentence):
                mentions.append({**base, "entity_id": m.entity_id, "entity_type": m.entity_type,
                                 "surface": m.surface, "start": m.start, "end": m.end})
    return (pd.DataFrame(sentences, columns=SENTENCE_COLUMNS),
            pd.DataFrame(mentions, columns=MENTION_COLUMNS))
