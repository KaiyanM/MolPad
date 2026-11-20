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
    return [s["command"] if s["kind"] == "dashboard" else "MESSAGE" for s in steps
            if s["kind"] not in ("data", "reasoning")]


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
    # both classes stay in the filter, so the bar sets them side by side
    assert commands(steps) == ["set filter1:Bacillota", "set filter2:Bacilli, Clostridia", "MESSAGE", "MESSAGE"]
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
    assert commands(steps).count("MESSAGE") == 3            # one per group, then the comparison
    assert commands(steps)[-3:] == [f"brush node:{groups[1]['clusters'][0]}", "MESSAGE", "MESSAGE"]
    msgs = [s["about"] for s in steps if s["kind"] == "message"]
    assert all(m["why"].startswith("picked as ") and "why" in m["write"] for m in msgs[:2])
    assert "compare the groups" in msgs[2]["write"]
    check_order(steps)


def test_L7_vague_criterion_splits_candidates():
    u = unit(steps=[{"kind": "ribbon", "criterion": "tightest_ribbon", "measure": "mean_width"}])
    leaf, steps = play([u], grouping="one_by_one")
    assert leaf == "L7"
    cmds = commands(steps)
    assert len(cmds) == 7 and all(c.startswith("brush node:") for c in cmds[0:6:2])
    assert cmds[-1] == "MESSAGE"


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


def test_L7_examples_per_class_say_why():
    u = unit(filters={"level2": ["Flavobacteriia", "Bacilli"]},
             steps=[{"kind": "example", "example_by": "level2_composition"}], descriptor={"pattern": True})
    leaf, steps = play([u], grouping="one_by_one")
    assert leaf == "L7"
    assert commands(steps) == ["set filter2:Flavobacteriia, Bacilli", "brush node:Group_3", "MESSAGE",
                               "brush node:Group_4", "MESSAGE", "MESSAGE"]
    assert "evaluate level2" in [s["action"] for s in steps if s["kind"] == "data"]
    msgs = [s["about"] for s in steps if s["kind"] == "message"]
    assert "of its features are Flavobacteriia" in msgs[0]["why"]
    assert "of its features are Bacilli" in msgs[1]["why"]


def test_level2_contrast_with_two_level1_keeps_every_class():
    u = unit(filters={"level1": ["Bacteroidota", "Bacillota"], "level2": ["Flavobacteriia", "Bacilli"],
                      "contrast": "level2"},
             steps=[{"kind": "example", "example_by": "level2_composition"}])
    assert [r["targets"] for r in u["runs"]] == [["Group_3"], ["Group_4"]]


def test_level2_contrast_counts_both_classes_and_compares_clusters():
    u = unit(filters={"level1": ["Bacillota"], "level2": ["Bacilli", "Clostridia"], "contrast": "level2"},
             steps=[{"kind": "feature_number"}], descriptor={"level2": True})
    for run in u["runs"]:
        mix = next(st for st in run["steps"] if st["op"] == "describe_level2")
        for cl, v in mix["result"].items():
            assert set(v["counts"]) == {"Bacilli", "Clostridia"}       # not 100% of the kept class
        assert not any("100%" in line for line in mix["findings"])
    last = u["runs"][-1]["steps"][-1]
    assert last["op"] == "compare_variants"
    both = set(u["runs"][0]["targets"]) & set(u["runs"][1]["targets"])
    assert last["result"]["in_all"] == sorted(both, key=load_dataset().cluster_number)
    assert any(line.startswith("shared main clusters") or line.startswith("no shared main cluster")
               for line in last["findings"])


def test_one_kept_class_has_no_class_mix():
    u = unit(filters={"level1": ["Bacillota"], "level2": ["Bacilli"]},
             steps=[{"kind": "feature_number"}], descriptor={"level2": True})
    assert "describe_level2" not in [st["op"] for st in u["runs"][0]["steps"]]


def test_absence_claims_are_caught():
    from agent.nodes import ABSENCE
    assert ABSENCE.search("This cluster contains only Bacilli (2,126) and no Clostridia")
    assert ABSENCE.search("Group_2 is 100% Betaproteobacteria")
    assert ABSENCE.search("it does not include Bacilli")
    for fine in ("It is a main Bacilli cluster but not a shared one", "no cluster is picked",
                 "Group_2 has no neighbours", "Only Group_4 is shared"):
        assert not ABSENCE.search(fine)


# ---- how groups are put in focus: together for one reason, one by one through the graph ----

def chain(*units):
    """An evidence chain: several sub-questions, each with the reason for its step."""
    for i, u in enumerate(units, 1):
        u["reason"] = f"reason {i}"
    return play(list(units), grouping="one_by_one")   # the display judgement does not split a chain


def test_chain_shows_clusters_picked_for_one_reason_together():
    a = unit("late", filters={"cols": "A", "level1": ["Actinomycetota"]},
             steps=[{"kind": "pattern", "criterion": "peak_at", "subject": "A", "position": "late"}])
    b = unit("other", filters={"level1": ["Bacillota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    picked = a["runs"][0]["targets"]
    assert len(picked) > 1
    leaf, steps = chain(a, b)
    assert leaf == "L7"
    shown = [c for c in commands(steps) if c.startswith(("brush node:", "select node:"))]
    assert shown[0].split(":")[1] == ",".join(picked)        # one action for the whole group
    first = next(s["about"] for s in steps if s["kind"] == "message")
    assert first["clusters"] == picked and first["purpose"] == "reason 1"


def test_chain_shows_clusters_found_through_the_graph_one_by_one():
    a = unit("neighbours", steps=[{"kind": "feature_number", "top_n": 1},
                                  {"kind": "network", "criterion": "neighbours"}])
    b = unit("other", filters={"level1": ["Bacillota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    group = a["runs"][0]["groups"][0]
    assert group["via"] == "network" and len(group["clusters"]) > 1
    _, steps = chain(a, b)
    shown = [c for c in commands(steps) if c.startswith("brush node:")]
    assert shown[:len(group["clusters"])] == [f"brush node:{c}" for c in group["clusters"]]


def test_chain_does_not_brush_the_same_clusters_twice():
    a = unit("claim a", filters={"level1": ["Actinomycetota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    b = unit("claim b", filters={"level1": ["Actinomycetota"]}, steps=[{"kind": "feature_number", "top_n": 1}],
             descriptor={"pattern": True})
    _, steps = chain(a, b)
    cmds = commands(steps)
    assert sum(c.startswith("brush node:") for c in cmds) == 1
    abouts = [s["about"] for s in steps if s["kind"] == "message"]
    assert "seen_before" not in abouts[0] and abouts[1]["seen_before"] is True


def test_chain_prints_the_reasoning_before_each_step():
    a = unit("claim a", filters={"level1": ["Actinomycetota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    b = unit("claim b", filters={"level1": ["Bacillota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    _, steps = chain(a, b)
    played = [s for s in steps if s["kind"] != "data"]
    reasons = [s for s in played if s["kind"] == "reasoning"]
    assert [r["text"] for r in reasons] == ["Step 1 of 2: claim a reason 1", "Step 2 of 2: claim b reason 2"]
    assert played[0] is reasons[0]                            # before the first filter
    assert played[played.index(reasons[1]) + 1]["command"] == "set filter1:Bacillota"
    assert steps[-1]["about"]["role"] == "conclusion"


def test_writer_never_drops_a_slot(monkeypatch):
    """A reply that leaves slots out is asked again for those slots; what is still empty is filled."""
    from agent import nodes
    a = unit("claim a", filters={"level1": ["Actinomycetota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    b = unit("claim b", filters={"level1": ["Bacillota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    _, steps = chain(a, b)
    asked = []

    def judge(schema, card, state, user, force_reasoning=False):
        asked.append(user.rsplit("\n\n", 1)[1])
        return {"texts": [{"slot": 1, "text": "first"}]}       # slot 2 and the conclusion never come

    monkeypatch.setattr(nodes, "_judge", judge)
    out = nodes.compose_messages({"question": "q", "steps": steps, "units": [a, b]})["steps"]
    texts = [s["text"] for s in out if s["kind"] == "message"]
    # one writer per step (side by side), the missing one asked again, the conclusion last
    assert sorted(asked[:3]) == ["Write only slot(s) 1.", "Write only slot(s) 2.", "Write only slot(s) 2."]
    assert asked[3] == "Write only slot(s) 3."
    assert len(texts) == 3 and texts[0] == "first" and all(texts)
    assert texts[2].startswith("No conclusion was written")


def test_writer_sends_the_playback_first_and_every_text_once(monkeypatch):
    from agent import nodes
    a = unit("claim a", filters={"level1": ["Actinomycetota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    b = unit("claim b", filters={"level1": ["Bacillota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    _, steps = chain(a, b)
    seen_findings = []

    def judge(schema, card, state, user, force_reasoning=False):
        seen_findings.append(user.split("FINDINGS OF THE DATA ACTIONS:")[1].split("MESSAGE SLOTS:")[0])
        wanted = [int(x) for x in user.rsplit("slot(s) ", 1)[1].rstrip(".").split(", ")]
        return {"texts": [{"slot": i, "text": f"text {i}"} for i in wanted]}

    events = []
    monkeypatch.setattr(nodes, "_judge", judge)
    token = nodes.EMIT.set(events.append)
    try:
        out = nodes.compose_messages({"question": "q", "steps": steps, "units": [a, b]})["steps"]
    finally:
        nodes.EMIT.reset(token)
    assert events[0]["event"] == "steps"
    played = events[0]["steps"]
    assert [s["slot"] for s in played if s["kind"] == "message"] == [0, 1, 2]
    assert all(s["text"] is None for s in played if s["kind"] == "message")
    assert [s["kind"] for s in played] == [s["kind"] for s in steps]      # same playback, same order
    sent = [(e["slot"], e["text"]) for e in events[1:]]
    assert sorted(sent) == [(0, "text 1"), (1, "text 2"), (2, "text 3")] and sent[-1][0] == 2
    assert [s["text"] for s in out if s["kind"] == "message"] == ["text 1", "text 2", "text 3"]
    # a step is written from its own findings; the conclusion reads all of them
    step_a = next(f for f in seen_findings[:2] if "Actinomycetota" in f)
    assert "Bacillota" not in step_a and "Bacillota" in seen_findings[2] and "Actinomycetota" in seen_findings[2]
    assert [s["kind"] for s in out if s["kind"] == "reasoning"] == ["reasoning"] * 2


def test_contrast_shows_a_shared_group_once_and_each_side_speaks():
    u = unit("contrast", filters={"level1": ["Actinomycetota", "Bacillota"], "contrast": "level1"},
             steps=[{"kind": "given", "clusters": ["Group_1"]}])
    other = unit("other", filters={"level1": ["Bacillota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    assert len(u["runs"]) == 2
    _, steps = chain(u, other)
    cmds = commands(steps)
    assert cmds[:4] == ["set filter1:Actinomycetota, Bacillota", "brush node:Group_1", "MESSAGE", "MESSAGE"]
    abouts = [s["about"] for s in steps if s["kind"] == "message"][:2]
    assert [a["run"] for a in abouts] == [0, 1] and abouts[1]["seen_before"] is True

