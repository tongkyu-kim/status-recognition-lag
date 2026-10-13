"""Unit test for the Japanese sentence splitter added 2026-10-14 (jp_diet corpus build)."""

from srl.text.segmentation import split_sentences_ja


def test_splits_on_japanese_period_without_trailing_space():
    text = "これは文です。これも文です。三つ目の文です。"
    sents = split_sentences_ja(text, min_chars=1)
    assert sents == ["これは文です。", "これも文です。", "三つ目の文です。"]


def test_drops_short_fragments():
    text = "短い。これは十分に長い文です。"
    sents = split_sentences_ja(text, min_chars=5)
    assert sents == ["これは十分に長い文です。"]


def test_empty_input():
    assert split_sentences_ja("") == []


def test_handles_question_and_exclamation_marks():
    text = "本当ですか？そうです！次の文。"
    sents = split_sentences_ja(text, min_chars=1)
    assert sents == ["本当ですか？", "そうです！", "次の文。"]
