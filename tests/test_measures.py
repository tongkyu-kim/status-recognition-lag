"""Arithmetic checks of implemented formulas.

The tiny inline tables below are hand-computable test fixtures used only to verify formulas;
they are not research data and are never written to disk.
"""

import math

import pandas as pd
import pytest

from srl.recognition.dictionary import compile_frames, load_frame_dictionary, score_text
from srl.recognition.index import recognition_index
from srl.recognition.lag import lag_standardized_difference
from srl.recognition.validation import cohen_kappa, krippendorff_alpha_nominal
from srl.text.language import detect_language
from srl.text.segmentation import split_sentences
from srl.trade.interdependence import hhi
from srl.trade.overlap import export_similarity_index, rca


def _exports(rows):
    return pd.DataFrame(rows, columns=["year", "iso3", "product", "value"])


def test_rca_balassa():
    ex = _exports([(2000, "AAA", "p1", 10.0), (2000, "AAA", "p2", 0.0),
                   (2000, "BBB", "p1", 0.0), (2000, "BBB", "p2", 10.0)])
    out = rca(ex).set_index(["iso3", "product"])["rca"]
    assert out[("AAA", "p1")] == pytest.approx(2.0)
    assert out[("AAA", "p2")] == pytest.approx(0.0)


def test_export_similarity_finger_kreinin():
    ex = _exports([(2000, "KOR", "p1", 5.0), (2000, "KOR", "p2", 5.0),
                   (2000, "AAA", "p1", 10.0)])
    out = export_similarity_index(ex, reference="KOR")
    assert out.loc[out["iso3"] == "AAA", "esi"].item() == pytest.approx(0.5)


def test_hhi():
    assert hhi([1, 1]) == pytest.approx(0.5)
    assert hhi([5]) == pytest.approx(1.0)


def test_cohen_kappa_hand_computed():
    # po = 0.75, pe = 0.5 -> kappa = 0.5
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "b", "b"]) == pytest.approx(0.5)


def test_krippendorff_alpha_nominal():
    perfect = pd.DataFrame({"c1": ["a", "b", "a"], "c2": ["a", "b", "a"]})
    assert krippendorff_alpha_nominal(perfect) == pytest.approx(1.0)
    # coincidences o = [[2,1],[1,4]], n = 8 -> alpha = 1 - 7 * 2 / 30
    data = pd.DataFrame({"c1": ["a", "a", "b", "b"], "c2": ["a", "b", "b", "b"]})
    assert krippendorff_alpha_nominal(data) == pytest.approx(1 - 14 / 30)


def test_recognition_index_orientation():
    h, v = pd.Series([3, 0, 0]), pd.Series([1, 2, 0])
    share = recognition_index(h, v, method="share")
    assert share[0] == pytest.approx(0.75) and share[1] == 0 and math.isnan(share[2])
    logit = recognition_index(h, v, method="logit")
    assert logit[0] > 0 > logit[1] and logit[2] == pytest.approx(0.0)


def test_lag_sign_convention():
    df = pd.DataFrame({"iso3": ["A", "B", "C"], "year": 2000,
                       "status": [1.0, 2.0, 3.0], "recog": [3.0, 2.0, 1.0]})
    lag = lag_standardized_difference(df, "status", "recog")
    # highest status + lowest recognition => largest positive (under-recognition) lag
    assert lag.idxmax() == 2 and lag[2] > 0 and lag[1] == pytest.approx(0.0)


def test_dictionary_longest_match_counts_once():
    compiled = compile_frames(load_frame_dictionary())
    counts = score_text("The two sides upgraded ties to a comprehensive strategic partnership.",
                        compiled)
    assert counts["frame_horizontal"] == 1
    assert score_text("양국은 포괄적 전략적 동반자 관계로 격상했다.", compiled)["frame_horizontal"] == 1


def test_language_and_segmentation_baselines():
    assert detect_language("한국 정부는 베트남과의 협력을 강화하기로 했다.") == "ko"
    assert detect_language("The government will expand cooperation with Viet Nam.") == "en"
    assert split_sentences("The U.S. said 3.5% growth. Korea agreed! Next.") == [
        "The U.S. said 3.5% growth.", "Korea agreed!", "Next."]
