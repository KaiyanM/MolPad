"""Leaf templates: slots + real data results -> ordered steps. No LLM."""

import pytest

from agent import leaves
from agent.data_tools import load_dataset
from agent.nodes import run_unit

NONE = {"cols": None, "level1": [], "level2": [], "level3_column": None, "level3_values": [],
        "level3_has_annotation": False, "external_concept": None, "contrast": "none"}


def unit(question="q", filters=None, steps=None, descriptor=None, state=None):
    ds = load_dataset()
    return run_unit(question, {**NONE, **(filters or {})}, {"steps": steps or []}, descriptor or {},
                    state or ds.default_state(), ds)


def play(units, needs_focus=True, network_area=False, grouping="together"):
    display = {"needs_focus": needs_focus, "network_area": network_area, "grouping": grouping}
    leaf = leaves.choose_leaf(units, display)
    return leaf, leaves.assemble(leaf, units, display)


def commands(steps):
    return [s["command"] if s["kind"] == "dashboard" else "MESSAGE" for s in steps if s["kind"] != "data"]


def check_order(steps):
    kinds = [s["kind"] for s in steps]
    n_data = kinds.count("data")
    assert kinds[:n_data] == ["data"] * n_data, "data actions come first"
    assert kinds[-1] == "message"


def test_L3_default():
    leaf, steps = play([unit(steps=[{"kind": "all"}], descriptor={"feature_number": True})], needs_focus=False)
    assert leaf == "L3" and commands(steps) == ["MESSAGE"]
    check_order(steps)


def test_L4_contrast_two_steps():
    u = unit(filters={"level1": ["Bacillota"], "level2": ["Bacilli", "Clostridia"], "contrast": "level2"},
             steps=[{"kind": "feature_number"}])
    leaf, steps = play([u], needs_focus=False)
    assert leaf == "L4"
    assert commands(steps) == ["set filter1:Bacillota", "set filter2:Bacilli", "MESSAGE",
                               "set filter2:Clostridia", "MESSAGE"]
    assert all(s["supported"] for s in steps if s["kind"] == "dashboard")
    check_order(steps)


def test_L4_table_search():
    u = unit(filters={"level1": ["Pseudomonadota"], "level3_column": "KEGG_ID", "level3_values": ["K11901"]},
             steps=[{"kind": "feature_lookup"}])
    leaf, steps = play([u], needs_focus=False)
    assert leaf == "L4"
    assert commands(steps) == ["set filter1:Pseudomonadota", "search table:K11901", "MESSAGE"]


def test_L5_single_focus_is_fully_supported():
    u = unit(filters={"level1": ["Pseudomonadota"]}, steps=[{"kind": "feature_number", "top_n": 1}],
             descriptor={"pattern": True})
    leaf, steps = play([u])
    assert leaf == "L5"
    assert commands(steps) == ["set filter1:Pseudomonadota", "brush node:Group_2", "MESSAGE"]
    assert all(s["supported"] for s in steps if s["kind"] == "dashboard")
    assert [s["action"] for s in steps if s["kind"] == "data"] == [
        "filter-level1-Pseudomonadota", "evaluate feature number and select cluster", "evaluate pattern"]
    check_order(steps)


def test_L6_compare_together():
    u = unit(filters={"level1": ["Pseudomonadota"]}, steps=[{"kind": "feature_number", "top_n": 2}])
    run = u["runs"][0]
    leaf, steps = play([u])
    assert leaf == "L6"
    a, b = run["targets"]
    shown = [f"brush node:{a},{b}" if run["joined"] else f"select node:{a},{b}"]
    assert commands(steps) == ["set filter1:Pseudomonadota"] + shown + ["MESSAGE"]


def test_L7_one_by_one_groups():
    u = unit(filters={"cols": "A"}, steps=[{"kind": "pattern", "criterion": "increase_and_decrease"}])
    groups = u["runs"][0]["groups"]
    assert [g["label"] for g in groups] == ["increase", "decrease"]
    leaf, steps = play([u])
    assert leaf == "L7"
    assert commands(steps).count("MESSAGE") == 2
    assert commands(steps)[-2:] == [f"brush node:{groups[1]['clusters'][0]}", "MESSAGE"]
    check_order(steps)


def test_L7_vague_criterion_splits_candidates():
    u = unit(steps=[{"kind": "ribbon", "criterion": "tightest_ribbon", "measure": "mean_width"}])
    leaf, steps = play([u], grouping="one_by_one")
    assert leaf == "L7"
    cmds = commands(steps)
    assert len(cmds) == 6 and all(c.startswith("brush node:") for c in cmds[0::2])


def test_L7_evidence_chain_ends_with_conclusion():
    a = unit("claim a", filters={"level1": ["Actinomycetota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    b = unit("claim b", filters={"level1": ["Bacillota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    leaf, steps = play([a, b])
    assert leaf == "L7"
    cmds = commands(steps)
    assert cmds[0] == "set filter1:Actinomycetota" and "set filter1:Bacillota" in cmds
    assert cmds[-2:] == ["MESSAGE", "MESSAGE"]
    assert "conclusion" in steps[-1]["about"]["write"]


def test_L8_one_group():
    u = unit(steps=[{"kind": "network", "criterion": "strongest_edge"}], descriptor={"pattern": True})
    leaf, steps = play([u], network_area=True)
    assert leaf == "L8" and commands(steps) == ["brush node:Group_2,Group_3", "MESSAGE"]


def test_L8_slider_and_each_pair():
    ds = load_dataset()
    u = unit(steps=[{"kind": "network", "criterion": "connected_pairs", "threshold": "max"}])
    leaf, steps = play([u], network_area=False)   # a moved slider forces the network leaf
    assert leaf == "L8"
    cmds = commands(steps)
    assert cmds[0] == f"set importance:{ds.slider_max}"
    assert cmds[2::2] == ["MESSAGE"] * len(u["runs"][0]["groups"])
    check_order(steps)


def test_current_selection_is_used():
    ds = load_dataset()
    state = {**ds.default_state(), "selected_clusters": ["Group_2", "Group_5"]}
    u = unit(steps=[{"kind": "given"}], descriptor={"level3_column": "GO_ID", "level3_mode": "coverage"},
             state=state)
    assert u["runs"][0]["targets"] == ["Group_2", "Group_5"]
    assert u["runs"][0]["steps"][0]["action"] == "select current cluster"


def test_unknown_values_are_dropped_and_reported():
    u = unit(filters={"level1": ["pseudomonadota", "Martian"], "cols": "cheese A"})
    assert u["filters"]["level1"] == ["Pseudomonadota"] and u["filters"]["cols"] == "A"
    assert u["dropped"] == ["level1 'Martian'"]


@pytest.mark.parametrize("steps, n_dash", [
    (leaves.leaf_L0(), 0),
    (leaves.leaf_L1("layout", "circle"), 1),
    (leaves.leaf_L2("which cluster?"), 0),
])
def test_L0_L1_L2(steps, n_dash):
    assert steps[-1]["kind"] == "message"
    dash = [s for s in steps if s["kind"] == "dashboard"]
    assert len(dash) == n_dash
    if dash:
        assert dash[0]["command"] == "set layout:circle" and dash[0]["supported"]


def test_unjoined_clusters_are_clicked():
    ds = load_dataset()
    state = {**ds.default_state(), "min_weight": 99}     # no edge is visible
    u = unit(steps=[{"kind": "given", "clusters": ["Group_2", "Group_7"]}], state=state)
    _, steps = play([u])
    assert commands(steps) == ["select node:Group_2,Group_7", "MESSAGE"]
    assert steps[-2]["supported"]


def test_table_search_is_not_repeated_per_group():
    u = unit(filters={"level3_column": "KEGG_ID", "level3_values": ["K03196"]},
             steps=[{"kind": "feature_lookup"}])
    _, steps = play([u], grouping="one_by_one")
    cmds = commands(steps)
    assert cmds.count("search table:K03196") == 1 and cmds.count("MESSAGE") > 1
