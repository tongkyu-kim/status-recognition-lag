"""Country/group mention matching in running text."""

import pytest

from srl.text.entities import default_matcher


def ids(text):
    return [m.entity_id for m in default_matcher().find(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Talks between North Korea and South Korea resumed.", ["PRK", "KOR"]),
        ("Tensions in the South China Sea persisted.", []),
        ("China and Viet Nam signed the agreement.", ["CHN", "VNM"]),
        ("한국은 베트남과 협력을 확대했다.", ["KOR", "VNM"]),       # particles attached
        ("남중국해 문제를 논의했다.", []),                          # shield
        ("한중간 논의가 이어졌다.", []),                             # 한중간 is not China
        ("한·중 정상회담이 열렸다.", ["CHN"]),                       # punctuated compound
        ("한·중동 협력 포럼", []),                                  # Middle East, not China
        ("대중국 수출이 증가했다.", ["CHN"]),                       # prefix 대-
        ("US officials met with us.", ["USA"]),                    # acronym case-sensitive
        ("Korean firms invested abroad.", []),                     # demonyms off by default
        ("한-아세안 특별정상회의", ["ASEAN"]),
    ],
)
def test_find_mentions(text, expected):
    assert ids(text) == expected


def test_mask_replaces_mentions():
    masked = default_matcher().mask("China and Thailand discussed trade.")
    assert masked == "[COUNTRY] and [COUNTRY] discussed trade."
