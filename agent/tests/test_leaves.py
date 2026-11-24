"""Leaf templates: slots + real data results -> ordered steps. No LLM."""

import pytest

from agent.core import leaves
from agent.core.data_tools import load_dataset
from agent.core.nodes import run_unit

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
            if s["kind"] not in ("data", "reasoning", "unit")]


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
    from agent.core.nodes import ABSENCE
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


def test_chain_opens_a_unit_before_each_step():
    a = unit("claim a", filters={"level1": ["Actinomycetota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    b = unit("claim b", filters={"level1": ["Bacillota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    _, steps = chain(a, b)
    played = [s for s in steps if s["kind"] != "data"]
    heads = [s for s in played if s["kind"] == "unit"]
    assert [(h["unit"], h["of"], h["question"], h["reason"]) for h in heads] == [
        (0, 2, "claim a", "reason 1"), (1, 2, "claim b", "reason 2")]
    assert played[0] is heads[0]                              # before the first filter
    assert played[played.index(heads[1]) + 1]["command"] == "set filter1:Bacillota"
    # every action and message of a step carries its unit; the conclusion stands outside
    assert [s["unit"] for s in played] == [0] * played.index(heads[1]) + [1] * (len(played) - played.index(heads[1]) - 1) + [None]
    assert steps[-1]["about"]["role"] == "conclusion"
    assert not [s for s in played if s["kind"] == "reasoning"]


def test_unit_overview_names_the_actions_in_order():
    a = unit("claim a", filters={"level1": ["Actinomycetota"]}, steps=[{"kind": "feature_number", "top_n": 1}])
    b = unit("claim b", steps=[{"kind": "given", "clusters": ["Group_5"]},
                               {"kind": "pattern", "criterion": "compare", "tool": "similar",
                                "between": "clusters", "a": {"subject": "A"}}])
    _, steps = chain(a, b)
    heads = [s for s in steps if s["kind"] == "unit"]
    assert heads[0]["overview"] == ("First set filter 1 to Actinomycetota, then brush Group_5 "
                                    "(top 1 by feature count).")
    # the second step read every level-1 value, so the filter the first step set is cleared
    assert heads[1]["overview"] == "First clear filter 1, then brush Group_3 (similar to Group_5 in A)."
    assert "set filter1:all" in commands(steps)


def test_single_question_is_one_unit_with_the_display_reason():
    u = unit("which is largest?", filters={"level1": ["Pseudomonadota"]},
             steps=[{"kind": "feature_number", "top_n": 1}])
    display = {"needs_focus": True, "network_area": False, "grouping": "together", "reason": "the largest one"}
    steps = leaves.assemble("L5", [u], display)
    played = [s for s in steps if s["kind"] != "data"]
    assert played[0]["kind"] == "unit" and (played[0]["of"], played[0]["reason"]) == (1, "the largest one")
    assert {s["unit"] for s in played} == {0}


def test_missing_similarity_scope_is_assumed_and_stated():
    u = unit("similar to 5?", steps=[{"kind": "given", "clusters": ["Group_5"]},
                                      {"kind": "pattern", "criterion": "compare", "tool": "similar",
                                       "between": "clusters"}])
    assert [(a["field"], a["used"]) for a in u["assumed"]] == [("match", "all")]
    _, steps = play([u])
    head = next(s for s in steps if s["kind"] == "unit")
    assert len(head["assumed"]) == 1 and "every sample group (A and C)" in head["assumed"][0]
    # a question that names the sample group leaves nothing to assume
    named = unit("similar to 5 in A?", steps=[{"kind": "given", "clusters": ["Group_5"]},
                                               {"kind": "pattern", "criterion": "compare", "tool": "similar",
                                                "between": "clusters", "a": {"subject": "A"}}])
    assert named["assumed"] == [] and named["runs"][0]["targets"] == ["Group_3"]


def test_writer_never_drops_a_slot(monkeypatch):
    """A reply that leaves slots out is asked again for those slots; what is still empty is filled."""
    from agent.core import nodes
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
    from agent.core import nodes
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
    assert [s["kind"] for s in out if s["kind"] == "unit"] == ["unit"] * 2
    # the client can tell which step a message belongs to, and which one is the conclusion
    assert [(s["unit"], s.get("role")) for s in played if s["kind"] == "message"] == [
        (0, None), (1, None), (None, "conclusion")]


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



def test_connectivity_without_a_picking_step_does_not_walk_over_every_cluster():
    """'Are the Alphaproteobacteria clusters connected to one another?' planned as all + connectivity."""
    from agent.core import nodes
    from agent.core.dataset import load_dataset
    ds = load_dataset()
    f = {"level1": [], "level2": ["Alphaproteobacteria"], "contrast": "none"}
    for steps in ([{"kind": "network", "criterion": "connectivity"}],
                  [{"kind": "all"}, {"kind": "network", "criterion": "connectivity"}]):
        u = nodes.run_unit("q", f, {"steps": steps}, {}, ds.default_state(), ds)
        run = u["runs"][0]
        assert 1 <= len(run["targets"]) <= 4, run["targets"]          # the clusters holding most of it
        assert len(run["groups"]) == 1 and run["groups"][0].get("via") != "network"
        ops = [s["op"] for s in run["steps"]]
        assert ops.index("select_by_feature_number") < ops.index("select_by_network")
        net = next(s for s in run["steps"] if s["op"] == "select_by_network")
        assert any(line.startswith(("links among", "no link among")) for line in net["findings"])
        cmds = [s["command"] for s in play([u])[1] if s["kind"] == "dashboard"]
        assert len([c for c in cmds if c.startswith(("brush node", "select node"))]) == 1   # shown together, once
    # no filter and nothing picked: a question about the whole network, nothing is brushed
    u = nodes.run_unit("q", {"level1": [], "level2": [], "contrast": "none"},
                       {"steps": [{"kind": "network", "criterion": "connectivity"}]}, {}, ds.default_state(), ds)
    assert u["runs"][0]["targets"] == [] and "connected components" in str(u["runs"][0]["steps"][-1]["findings"])


def test_a_long_group_is_never_put_in_focus_cluster_by_cluster():
    group = {"label": "x", "clusters": [f"Group_{i}" for i in range(1, 11)], "via": "network"}
    assert leaves._groups({"groups": [group]}) == [group]
    short = {"label": "x", "clusters": ["Group_1", "Group_2"], "via": "network"}
    assert [g["clusters"] for g in leaves._groups({"groups": [short]})] == [["Group_1"], ["Group_2"]]


def test_common_patterns_under_a_filter_are_those_of_the_main_clusters_not_every_similar_pair():
    """'Which clusters show the common patterns of Alphaproteobacteria' planned as similar between clusters."""
    u = unit(filters={"level2": ["Alphaproteobacteria"]},
             steps=[{"kind": "pattern", "criterion": "compare", "tool": "similar", "between": "clusters"}],
             descriptor={"pattern": True})
    run = u["runs"][0]
    ops = [s["op"] for s in run["steps"]]
    assert "select_by_feature_number" in ops and "select_by_comparison" not in ops and "select_by_similarity" not in ops
    assert ops.count("describe_pattern") == 1 and 1 <= len(run["targets"]) <= 4
    assert '"Common patterns" was read as the patterns of the clusters that hold most' in u["assumed"][0]["text"]
    cmds = [c for c in commands(play([u])[1]) if c.startswith(("brush node", "select node"))]
    assert len(cmds) == 1
    # with no filter the question is about all clusters, and pairs that look alike are the answer
    v = unit(steps=[{"kind": "pattern", "criterion": "compare", "tool": "similar", "between": "clusters"}])
    assert "select_by_comparison" in [s["op"] for s in v["runs"][0]["steps"]] and not v["assumed"]


def test_the_network_step_says_which_clusters_it_took():
    u = unit(filters={"level2": ["Alphaproteobacteria"]}, steps=[{"kind": "network", "criterion": "connectivity"}])
    assert "read as the clusters that hold most of the filtered features" in u["assumed"][0]["text"]
