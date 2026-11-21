"""The Ribbon class: one cluster in one sample group, and similarity between ribbons. No LLM."""

import numpy as np
import pytest

from agent.data_tools import Session, load_dataset
from agent.ribbon import MissingInput, Ribbon, similar_clusters

LABELS = ["A_1", "A_2", "A_3", "A_4", "A_5"]


def ribbon(cluster, curve, subject="A", spread=0.2):
    """Three features around one mean curve."""
    curve = np.asarray(curve, dtype=float)
    labels = [f"{subject}_{i}" for i in range(1, len(curve) + 1)]
    return Ribbon.from_values(cluster, subject, [curve - spread, curve, curve + spread], labels)


def test_fields_come_from_the_detectors():
    r = ribbon("Group_1", [0, 1, 2, 3, 4])
    assert (r.cluster, r.subject, r.shape, r.n_features) == ("Group_1", "A", "increase", 3)
    assert r.peak == "A_5" and r.mean == (0.0, 1.0, 2.0, 3.0, 4.0)
    assert r.width_mean == pytest.approx(0.4) and r.width_trend == "steady"
    d = r.describe()
    assert d["shape"] == "increase" and d["ribbon_width"] == pytest.approx(0.4) and d["text"]


def test_describe_pattern_reads_the_ribbons():
    s = Session(load_dataset())
    s.run("select_given", clusters=["Group_5"])
    out = s.run("describe_pattern")["cluster"]["Group_5"]
    assert set(out) == {"A", "C"}
    assert {"shape", "peak", "fitted_shape", "fit_r2", "ribbon_width", "ribbon_trend", "text"} <= set(out["A"])


def test_similarity_of_two_curves():
    up, up2, down = ribbon("a", [0, 1, 2, 3, 4]), ribbon("b", [1, 3, 5, 7, 9]), ribbon("c", [4, 3, 2, 1, 0])
    same = up.similarity(up2)
    assert same["similar"] and same["r"] == pytest.approx(1.0) and "r = 1.00" in same["note"]
    assert not up.similarity(down)["similar"]


def test_two_flat_curves_are_similar_and_have_no_r():
    flat = ribbon("a", [1, 1, 1, 1, 1]).similarity(ribbon("b", [3, 3.1, 3, 3.1, 3]))
    assert flat["similar"] and flat["r"] is None and flat["note"] == "both flat"


def test_similarity_needs_one_sample_group():
    with pytest.raises(ValueError, match="one sample group"):
        ribbon("a", [0, 1, 2, 3, 4], "A").similarity(ribbon("b", [0, 1, 2, 3, 4], "C"))


def ribbons():
    """b follows a in A and in C; c follows a in A only."""
    return {
        "a": {"A": ribbon("a", [0, 1, 2, 3, 4], "A"), "C": ribbon("a", [4, 3, 2, 1, 0], "C")},
        "b": {"A": ribbon("b", [1, 2, 3, 4, 5], "A"), "C": ribbon("b", [9, 7, 5, 3, 1], "C")},
        "c": {"A": ribbon("c", [0, 2, 4, 6, 8], "A"), "C": ribbon("c", [0, 1, 2, 3, 4], "C")},
    }


def test_missing_match_is_an_error_with_a_default():
    with pytest.raises(MissingInput) as err:
        similar_clusters(ribbons(), ["a"])
    m = err.value
    assert (m.field, m.default, m.options) == ("match", "all", ["all", "any", "A", "C"])
    assert "every sample group (A and C)" in m.say


def test_match_all_any_and_one_sample_group():
    r = ribbons()
    assert similar_clusters(r, ["a"], match="all")["clusters"] == ["b"]
    assert similar_clusters(r, ["a"], match="any")["clusters"] == ["b", "c"]
    assert similar_clusters(r, ["a"], subjects=["C"])["clusters"] == ["b"]      # one group: nothing to assume
    assert similar_clusters(r, ["a"], match="A")["clusters"] == ["b", "c"]      # a sample group as the choice
    # the per-sample-group answer is always there
    assert similar_clusters(r, ["a"], match="all")["similar_per_subject"] == {"A": ["b", "c"], "C": ["b"]}


def test_no_base_is_an_error():
    with pytest.raises(ValueError, match="compare with"):
        similar_clusters(ribbons(), [])
