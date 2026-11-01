"""Pattern detectors on synthetic series. No LLM, no dashboard data."""

import numpy as np
import pytest

from agent import patterns as P

LABELS = ["A_1", "A_2", "A_3", "A_4", "A_5"]
AXIS = P.TimeAxis.of(LABELS)


def test_time_axis_from_labels_and_gaps():
    axis = P.TimeAxis.of(["C_1", "C_3", "C_4", "C_5"])
    assert axis.times == (1.0, 3.0, 4.0, 5.0)
    assert axis.gaps() == [2.0]
    assert axis.gaps([1, 2, 3, 4, 5, 6]) == [2.0, 6.0]
    assert P.TimeAxis.of(["wk a", "wk b"]).times == (0.0, 1.0)
    assert axis.phase(0, P.Thresholds()) == "early" and axis.phase(3, P.Thresholds()) == "late"


@pytest.mark.parametrize("y, direction", [
    ([0, 1, 2, 3, 4], "increase"),
    ([4, 3, 2, 1, 0], "decrease"),
    ([0, 1, 2, 4, 3.9], "increase"),          # one small step back is still a steady rise
    ([0.0, 0.1, 0.05, 0.12, 0.1], "even"),
    ([0, 2, 0, 2, 0], "mixed"),
])
def test_trend_direction(y, direction):
    assert P.trend(y, AXIS)["direction"] == direction


def test_trend_numbers_and_missing_points():
    t = P.trend([0, 1, np.nan, 3, 4], AXIS)
    assert t["direction"] == "increase" and t["n_points"] == 4
    assert t["net_change"] == 4 and t["slope"] == pytest.approx(1.0)


def test_peaks_where_and_how_many():
    one = P.peaks([0, 1, 3, 1, 0], AXIS)
    assert one["n_peaks"] == 1 and one["peaks"][0]["at"] == "A_3" and one["peaks"][0]["phase"] == "mid"
    assert one["peaks"][0]["interior"]
    two = P.peaks([0, 3, 0, 3, 0], AXIS)
    assert two["n_peaks"] == 2 and two["n_interior_peaks"] == 2 and two["n_troughs"] == 3
    edge = P.peaks([0, 1, 2, 3, 4], AXIS)
    assert edge["n_peaks"] == 1 and edge["peaks"][0]["at"] == "A_5" and not edge["peaks"][0]["interior"]
    assert edge["highest"]["phase"] == "late" and edge["lowest"]["at"] == "A_1"


def test_small_bumps_and_even_curves_are_not_peaks():
    assert P.peaks([0, 3, 2.9, 3.0, 0], AXIS)["n_peaks"] == 1       # the second top is not prominent
    assert P.peaks([0.0, 0.1, 0.0, 0.1, 0.0], AXIS)["n_peaks"] == 0   # even curve


def test_changes():
    c = P.changes([0, 1, 4, 2, 2], AXIS)
    assert c["largest_rise"]["from"] == "A_2" and c["largest_rise"]["change"] == 3
    assert c["largest_fall"]["to"] == "A_4" and c["turning_points"] == 1
    assert P.changes([0, 1, 2, 3, 4], AXIS)["largest_fall"] is None


def test_missingness_per_timepoint_and_constant_features():
    m = np.array([[1, 2, np.nan, 4, 5],
                  [1, np.nan, np.nan, 4, 5],
                  [0, 0, 0, 0, 0],
                  [1, 2, 3, 4, 5]], dtype=float)
    r = P.missingness(m, AXIS)
    assert r["per_timepoint"]["A_3"] == {"n": 2, "fraction": 0.5}
    assert r["most_missing_timepoint"] == "A_3"
    assert r["features_complete"] == 2 and r["features_with_missing"] == 2
    assert r["features_constant"] == 1 and r["fraction_missing"] == pytest.approx(3 / 20)
    zero = P.missingness(m, AXIS, missing_value=0)
    assert zero["features_all_missing"] == 1 and zero["per_timepoint"]["A_1"]["n"] == 1


def test_spread_ribbon_and_consistency():
    rng = np.random.default_rng(0)
    base = np.array([0, 1, 2, 3, 4], dtype=float)
    tight = base + rng.normal(0, 0.05, (50, 5))
    wide = base + rng.normal(0, 2.0, (50, 5))
    a, b = P.spread(tight, AXIS), P.spread(wide, AXIS)
    assert a["ribbon_width"]["mean"] < b["ribbon_width"]["mean"]
    assert a["sd"]["mean"] < b["sd"]["mean"]
    assert a["consistent"] and a["consistency"] > 0.95 > b["consistency"]
    one_wide = tight.copy()
    one_wide[:, 2] += rng.normal(0, 3, 50)
    assert P.spread(one_wide, AXIS)["ribbon_width"]["widest_at"] == "A_3"


def test_width_measures_and_area_on_uneven_times():
    m = np.array([[0, 0, 0, 0, 0], [1, 2, 3, 2, 1]], dtype=float)
    w = P.width(m, AXIS)
    assert w["per_timepoint"]["A_3"] == 3 and w["mean"] == pytest.approx(1.8)
    assert w["max"] == 3 and w["widest_at"] == "A_3" and w["narrowest_at"] == "A_1"
    assert w["area"] == pytest.approx(8.0)                   # trapezoid over times 1..5
    assert w["variability"]["sd"] == pytest.approx(np.std([1, 2, 3, 2, 1], ddof=1))
    uneven = P.TimeAxis.of(["C_1", "C_3", "C_4", "C_5"])     # no C_2: the first step counts twice
    u = P.width(np.array([[0, 0, 0, 0], [2, 2, 2, 2.0]]), uneven)
    assert u["area"] == pytest.approx(8.0) and u["area_per_time"] == pytest.approx(2.0)
    gap = m.copy()
    gap[:, 1] = np.nan                                        # a timepoint with no values is skipped
    assert P.width(gap, AXIS)["n_timepoints"] == 4 and "A_2" not in P.width(gap, AXIS)["per_timepoint"]


@pytest.mark.parametrize("w, direction", [
    ([0.2, 0.5, 0.9, 1.2, 1.6], "expanding"),
    ([1.6, 1.2, 0.9, 0.5, 0.2], "contracting"),
    ([1.0, 1.02, 0.98, 1.01, 1.0], "steady"),
    ([0.2, 1.5, 0.2, 1.5, 0.2], "mixed"),
])
def test_width_trend(w, direction):
    assert P.width_trend(w, AXIS)["direction"] == direction


def test_ribbon_and_score():
    m = np.array([[0, 0, 0, 0, 0], [0.2, 0.5, 0.9, 1.2, 1.6]])
    r = P.ribbon(m, AXIS)
    assert r["trend"]["direction"] == "expanding" and r["n_features"] == 2
    assert P.ribbon_score(r, "mean_width") == pytest.approx(0.88)
    assert P.ribbon_score(r, "max_width") == pytest.approx(1.6)
    assert P.ribbon_score(r, "slope") > 0
    assert set(P.TIGHTNESS) == {"mean_width", "max_width", "area"}
    with pytest.raises(ValueError):
        P.ribbon_score(r, "relative_width")
    assert "ribbon widens" in P.describe(m, LABELS)["text"]


def test_divergence_between_subgroups():
    m = np.vstack([np.tile([0, 0, 0, 0, 0.0], (5, 1)), np.tile([0, 0, 2, 0, 0.0], (5, 1))])
    d = P.divergence(m, ["x"] * 5 + ["y"] * 5, AXIS)
    assert d["largest_gap"] == {"at": "A_3", "gap": 2.0, "highest": "y", "lowest": "x"}
    assert P.divergence(m, ["x"] * 10, AXIS)["n_groups"] == 1


@pytest.mark.parametrize("y, shape", [
    ([0, 1, 2, 3, 4], "increase"), ([4, 3, 2, 1, 0], "decrease"), ([0, 1, 3, 1, 0], "hump"),
    ([3, 1, 0, 1, 3], "dip"), ([0, 3, 0, 3, 0], "multi-peak"), ([0, 0.1, 0, 0.1, 0], "even"),
])
def test_describe_shape_and_text(y, shape):
    d = P.describe(np.tile(np.array(y, dtype=float), (3, 1)), LABELS)
    assert d["shape"] == shape
    assert d["text"].lower().startswith(("steady " + shape, shape))
    assert set(d) >= {"mean", "trend", "peaks", "changes", "missingness", "spread", "text"}


def test_describe_reports_missingness_and_can_drop_constant_features():
    rising = np.tile(np.arange(5.0), (2, 1))
    flat = np.zeros((8, 5))
    m = np.vstack([rising, flat])
    all_in = P.describe(m, ["C_1", "C_3", "C_4", "C_5", "C_6"], expected_times=[1, 2, 3, 4, 5, 6])
    assert all_in["missingness"]["fraction_constant"] == 0.8
    assert "80.0% of features are constant" in all_in["text"]
    assert "no measurement at time 2" in all_in["text"]
    varying = P.describe(m, LABELS, drop_constant=True)
    assert varying["shape"] == "increase" and varying["spread"]["n_features"] == 2
    assert varying["trend"]["net_change"] == 4 and all_in["trend"]["net_change"] == pytest.approx(0.8)


@pytest.mark.parametrize("y, shape, model", [
    ([0, 1, 2, 3, 4], "increase", "linear"), ([4, 3, 2, 1, 0], "decrease", "linear"),
    ([3, 1, 0, 1, 3], "U", "quadratic"), ([0, 2, 3, 2, 0], "n", "quadratic"),
    ([5, 1, 0.2, 0, 0], "L", "early"), ([0, 3, 3.8, 4, 4], "early_rise", "early"),
    ([0, 0, 0.2, 1, 5], "J", "late"), ([4, 4, 3.8, 3, 0], "late_drop", "late"),
    ([0, 0, 4, 0, 0], "peak", "bump"), ([0, 0, 0, 3, 3], "step_up", "step"),
    ([0, 1, 4, 9, 16], "increase", "quadratic"),          # a bent rise is not a U
    ([0.0, 0.1, 0.0, 0.1, 0.0], "flat", "flat"),
])
def test_fit_picks_the_function(y, shape, model):
    f = P.fit_curve(y, AXIS)
    assert (f.shape, f.model) == (shape, model) and f.fits and f.r2 >= 0.8


def test_fit_irregular_and_too_short():
    zigzag = P.fit_curve([0, 3, 0, 3, 0], AXIS)
    assert zigzag.shape == "irregular" and not zigzag.fits
    assert P.fit_curve([0, 1], P.TimeAxis.of(LABELS[:2])).shape == "unknown"
    assert P.fit_curve([0, 1, 2], P.TimeAxis.of(LABELS[:3])).model == "linear"   # no curve on 3 points


def test_fit_predicts_missing_timepoints():
    f = P.fit_curve([4, 1, np.nan, 1, 4.2], AXIS)        # A_3 was not measured
    assert f.shape == "U" and f.n_points == 4 and f.at == pytest.approx(3, abs=0.1)
    assert f.predict([3])[0] < 1 and f.predict([1, 5]) == pytest.approx([4, 4.2], abs=0.2)
    gap = P.fit_curve([0, 2, 3, 4], P.TimeAxis.of(["C_1", "C_3", "C_4", "C_5"]))
    assert gap.predict([2])[0] == pytest.approx(1.0)      # time 2 is absent from the axis
    d = P.describe(np.tile([5, 1, 0.2, 0, 0.0], (3, 1)), LABELS)
    assert d["fit"]["shape"] == "L" and "Fitted overall shape: L" in d["text"]


@pytest.mark.parametrize("a, b, relation", [
    ([0, 1, 2, 3, 4], [4, 3, 2, 1, 0], "opposite"),
    ([0, 2, 3, 2, 0], [3, 1, 0, 1, 3], "opposite"),            # n against U
    ([5, 1, 0.2, 0, 0], [0, 0, 0.2, 1, 5], "opposite"),        # L against J: one falls, one rises
    ([0, 1, 2, 3, 4], [10, 11, 12.5, 13, 14], "similar"),      # the level does not matter
    ([0, 0, 1, 3, 9], [0, 0, 1, 2, 3], "diverging"),
    ([9, 3, 1, 0, 0], [3, 2, 1, 0, 0], "converging"),
])
def test_compare_relations(a, b, relation):
    assert relation in P.compare(a, AXIS, b, AXIS)["relations"]


def test_compare_needs_a_shape_on_both_sides():
    flat = [0.0, 0.1, 0.0, 0.1, 0.0]
    r = P.compare([0, 1, 2, 3, 4], AXIS, flat, AXIS)
    assert r["flat"] == [False, True] and "opposite" not in r["relations"] and "similar" not in r["relations"]
    assert P.compare(flat, AXIS, flat, AXIS)["relations"] == ["similar"]
    zigzag = P.compare([0, 3, 0, 3, 0], AXIS, [3, 0, 3, 0, 3], AXIS)     # no function fits either
    assert zigzag["fit_a"]["shape"] == "irregular" and zigzag["relations"] == []


def test_compare_shifted_curve():
    axis = P.TimeAxis.of([f"t_{i}" for i in range(1, 9)])
    r = P.compare([0, 0, 0, 4, 0, 0, 0, 0], axis, [0, 0, 0, 0, 0, 4, 0, 0], axis)
    assert "shifted" in r["relations"] and r["lag"]["leader"] == "a"
    assert r["lag"]["by"] == pytest.approx(2, abs=0.3)


def test_compare_on_different_time_axes_and_on_windows():
    other = P.TimeAxis.of(["C_1", "C_3", "C_4", "C_5"])
    r = P.compare([0, 1, 2, 3, 4], AXIS, [4, 2, 1, 0], other)       # C has no timepoint 2
    assert r["range_a"] == [1.0, 5.0] and "opposite" in r["relations"]
    # first half against second half of one fitted curve, each read from its own start to its end
    hump = [0, 2, 3, 2, 0]
    halves = P.compare(hump, AXIS, hump, AXIS, on="position", range_a=(1, 3), range_b=(3, 5))
    assert "opposite" in halves["relations"] and halves["direction"] == [1, -1]
    assert P.strength(halves, "opposite") == pytest.approx(-halves["r"])
    # the foot of an L is flat, so the two halves of an L are not opposite
    ell = [5, 1, 0.2, 0, 0]
    foot = P.compare(ell, AXIS, ell, AXIS, on="position", range_a=(1, 3), range_b=(3, 5))
    assert foot["flat"] == [False, True] and "opposite" not in foot["relations"]
    assert P.window(AXIS, end=3) == [0, 1, 2] and P.window(AXIS, start=3) == [2, 3, 4]
