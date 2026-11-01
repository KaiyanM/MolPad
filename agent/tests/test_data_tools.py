"""Data actions on the real CSVs. No LLM."""

import pytest

from agent.data_tools import Session, load_dataset


@pytest.fixture(scope="module")
def ds():
    return load_dataset()


def test_dataset_shape(ds):
    assert ds.subjects == {"A": ["A_1", "A_2", "A_3", "A_4", "A_5"], "C": ["C_1", "C_3", "C_4", "C_5"]}
    assert ds.clusters == [f"Group_{i}" for i in range(1, 11)]
    assert ds.level1_values == ["Actinomycetota", "Bacillota", "Bacteroidota", "Pseudomonadota"]
    assert ds.default_state()["min_weight"] == ds.default_threshold


def test_level1_counts_sum_to_total(ds):
    s = Session(ds)
    n = s.run("filter_level1", value="Actinomycetota")["n_features"]
    r = s.run("select_by_feature_number", top_n=1)
    assert sum(r["features_per_cluster"].values()) == n == r["total"]
    assert len(r["clusters"]) == 1 and s.targets == r["clusters"]


def test_feature_number_cover_rule(ds):
    s = Session(ds)
    s.run("filter_level1", value="Pseudomonadota")
    r = s.run("select_by_feature_number")
    assert r["share_of_selected"] >= 0.5
    assert r["clusters"][0] == "Group_2"


def test_strongest_edge(ds):
    s = Session(ds)
    r = s.run("select_by_network", criterion="strongest_edge")
    assert s.targets == ["Group_2", "Group_3"]
    assert r["edge"]["weight"] == pytest.approx(5.007, abs=1e-3)


def test_threshold_changes_edges(ds):
    s = Session(ds)
    default = s.run("select_by_network", criterion="connected_pairs")["groups"]
    top = s.run("select_by_network", criterion="connected_pairs", threshold="max")
    assert top["threshold"] == ds.slider_max
    assert 0 < len(top["groups"]) < len(default)
    assert s.run("select_by_network", criterion="isolated", threshold="min")["groups"] == []


def test_pattern_groups(ds):
    s = Session(ds)
    s.run("filter_cols", subject="A")
    r = s.run("select_by_pattern", criterion="increase_and_decrease")
    assert [g["label"] for g in r["groups"]] == ["increase", "decrease"]
    assert set(r["shape_per_cluster"]["Group_1"]) == {"A"}


def test_ribbon_definitions(ds):
    r = Session(ds).run("select_by_ribbon", criterion="tightest_ribbon")
    assert set(r["definitions"]) == {"mean_width", "max_width", "area"} and r["measure"] == "all"
    picks = {tuple(d["ranking"]) for d in r["definitions"].values()}
    assert len(r["groups"]) == len(picks)                    # definitions that agree share a group
    assert all(len(d["ranking"]) == 1 for d in r["definitions"].values())
    assert r["definitions_agree"] == (len(picks) == 1)
    one = Session(ds).run("select_by_ribbon", criterion="widest_ribbon", measure="area", top_n=2)
    assert list(one["definitions"]) == ["area"] and len(one["groups"]) == 2
    v = one["definitions"]["area"]["value_per_cluster"]
    assert v[one["groups"][0]["clusters"][0]] >= v[one["groups"][1]["clusters"][0]]
    a = Session(ds).run("select_by_ribbon", criterion="expanding_ribbon", subject="A")
    assert a["subjects"] == ["A"]
    assert all(a["per_cluster"][c]["A"]["width_trend"] == "expanding" for c in a["groups"][0]["clusters"])
    assert "error" in Session(ds).run("select_by_ribbon", criterion="tightest_ribbon", measure="relative")


def test_level3_ids(ds):
    s = Session(ds)
    r = s.run("filter_level3", column="KEGG_ID", values=["ko:K03196", "K99999"])
    assert r["features_per_id"]["K03196"] == r["n_features"] > 0
    assert r["features_per_id"]["K99999"] == 0
    look = s.run("select_by_feature_lookup")
    assert sum(look["features_per_cluster"].values()) == r["n_features"]


def test_descriptors(ds):
    s = Session(ds)
    s.run("select_given", clusters=["cluster_3", "2"])
    assert s.targets == ["Group_3", "Group_2"]
    cov = s.run("describe_level3", column="GO_ID", mode="coverage")
    assert set(cov) == {"Group_2", "Group_3"}
    comp = s.run("describe_level2")["Group_2"]
    assert sum(comp["counts"].values()) == comp["total"]
    pat = s.run("describe_pattern")["cluster"]["Group_3"]
    assert set(pat) == {"A", "C"} and pat["A"]["peak"] in ds.subjects["A"]


def test_bad_argument_is_reported_not_raised(ds):
    assert "error" in Session(ds).run("filter_level1", value="Nope")
    assert "error" in Session(ds).run("drop_table")


def test_comparison_between_subjects_windows_and_clusters(ds):
    s = Session(ds)
    r = s.run("select_by_comparison", tool="similar", between="subjects", a={"subject": "A"}, b={"subject": "C"})
    assert r["time_range"] == {"a": [1.0, 5.0], "b": [1.0, 5.0]}
    assert s.targets == r["groups"][0]["clusters"] and "Group_3" in s.targets
    assert all("similar" in r["value_per_cluster"][c]["relations"] for c in s.targets)
    assert r["value_per_cluster"]["Group_9"]["shape_a"] == "L"
    # a cluster that is flat in one cheese is not opposite, it is reported apart
    opp = s.run("select_by_comparison", tool="opposite")
    assert not set(opp["groups"][0]["clusters"]) & set(opp["flat_on_one_side"])

    w = s.run("select_by_comparison", tool="opposite", between="windows",
              a={"subject": "A", "start": "A_1", "end": "A_3"}, b={"subject": "A", "start": "A_3", "end": "A_5"})
    assert w["time_range"] == {"a": [1.0, 3.0], "b": [3.0, 5.0]}
    assert s.targets == ["Group_6"]          # peaks at A_3: up, then down
    half = s.run("select_by_comparison", tool="opposite", between="windows", a={"subject": "A"})
    assert half["time_range"] == w["time_range"]
    # the fitted function is read between timepoints, so a window may be two timepoints long
    short = s.run("select_by_comparison", tool="opposite", between="windows",
                  a={"subject": "C", "start": "C_1", "end": "C_3"}, b={"subject": "C", "start": "C_4", "end": "C_5"})
    assert short["time_range"] == {"a": [1.0, 3.0], "b": [4.0, 5.0]}

    s = Session(ds)                          # no clusters picked yet: every pair is tried
    p = s.run("select_by_comparison", tool="opposite", between="clusters", a={"subject": "A"}, top_n=2)
    assert len(p["groups"]) == 2 and all(len(g["clusters"]) == 2 for g in p["groups"])
    s.run("select_given", clusters=["3"])    # a picked cluster is the one the others are compared with
    ref = s.run("select_by_comparison", tool="opposite", between="clusters", a={"subject": "A"})
    assert ref["groups"] and all(g["clusters"][0] == "Group_3" for g in ref["groups"])


def test_comparison_rejects_empty_windows_and_unknown_tools(ds):
    s = Session(ds)
    empty = s.run("select_by_comparison", tool="opposite", between="windows",
                  a={"subject": "A", "start": "A_3", "end": "A_3"}, b={"subject": "A", "start": "A_3", "end": "A_5"})
    assert "start before its end" in empty["error"]
    assert "error" in s.run("select_by_comparison", tool="mirror")
    pat = s.run("describe_pattern")["cluster"]["Group_9"]["A"]
    assert pat["fitted_shape"] == "L" and pat["fit_r2"] > 0.9
