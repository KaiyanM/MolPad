"""Findings of the data actions, and the evidence each message points to. No LLM."""

import pytest

from agent import findings as F
from agent import leaves
from agent.data_tools import Session, load_dataset
from agent.tests.test_leaves import play, unit


@pytest.fixture(scope="module")
def ds():
    return load_dataset()


def test_every_data_action_has_a_rule():
    assert set(Session.OPS) | {"llm_search"} <= set(F.RULES)


@pytest.mark.parametrize("ops", [
    [("select_all", {}), ("describe_pattern", {})],
    [("select_all", {}), ("describe_level2", {})],
    [("select_by_comparison", {"tool": "opposite", "between": "clusters"})],
    [("select_by_network", {"criterion": "connected_pairs", "threshold": "min"})],
])
def test_large_results_fit_the_budget(ds, ops):
    s = Session(ds)
    for op, args in ops:
        result = s.run(op, **args)
    lines = F.conclude(op, args, result)
    assert sum(len(x) + 1 for x in lines) <= F.FINDINGS_CHARS
    assert not any(x.startswith("failed") for x in lines)


def test_all_clusters_reach_the_findings_in_dashboard_order(ds):
    s = Session(ds)
    s.run("select_all")
    lines = F.conclude("describe_pattern", {}, s.run("describe_pattern"))
    named = [x.split(" in ")[0] for x in lines]
    assert list(dict.fromkeys(named)) == ds.clusters        # Group_1 .. Group_10, none missing


def test_over_budget_keeps_whole_lines():
    lines = [f"line {i} " + "x" * 50 for i in range(100)]
    kept = F.fit(lines, limit=500)
    assert sum(len(x) + 1 for x in kept) <= 500
    assert kept[:-1] == lines[:len(kept) - 1]
    assert kept[-1] == f"... {100 - len(kept) + 1} more lines in the evidence"


def test_ribbon_findings_name_each_definition(ds):
    lines = F.conclude("select_by_ribbon", {}, Session(ds).run("select_by_ribbon", criterion="tightest_ribbon"))
    text = "\n".join(lines)
    assert "by mean width: Group_3" in text and "by area: Group_10" in text
    assert "the definitions disagree" in text


def test_errors_are_one_line():
    assert F.conclude("select_by_ribbon", {}, {"error": "ValueError: bad"}) == ["failed: ValueError: bad"]


def test_each_message_points_to_its_own_run():
    u = unit(steps=[{"kind": "ribbon", "criterion": "tightest_ribbon"}])
    u2 = unit(steps=[{"kind": "feature_number", "top_n": 1}], descriptor={"pattern": True})
    leaf, steps = play([u, u2], grouping="one_by_one")
    data = {s["id"]: s for s in steps if s["kind"] == "data"}
    assert all(s["findings"] for s in data.values())
    messages = [s for s in steps if s["kind"] == "message"]
    for m in messages[:-1]:
        assert m["evidence"] and all(data[i]["unit"] == m["about"]["unit"] for i in m["evidence"])
    assert messages[-1]["evidence"] == list(data)          # the conclusion rests on all of them


def test_leaves_without_data_have_no_evidence():
    for steps in (leaves.leaf_L0(), leaves.leaf_L1("layout", "circle"), leaves.leaf_L2("which cluster?")):
        assert all(s["evidence"] == [] for s in steps if s["kind"] == "message")
