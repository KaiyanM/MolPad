"""The frame pipeline from question to playback, with every LLM call stubbed. No API key."""

import pytest

from agent.core import frame, graph, nodes
from agent.core.schemas import Frame, Plans, SubFrames

QUESTION = "Which clusters have a similar shape to the cluster that is most enriched for Actinomycetota?"

PARSE = Frame(kind="data", shape="multi_step", reason="needs the reference cluster first",
              mentions=[{"text": "Actinomycetota", "role": "condition"}],
              target=["feature_number", "pattern"], measure=["pattern"], compare="curves").model_dump()

SUBS = SubFrames(sub_frames=[
    {"question": "Which cluster holds the most Actinomycetota features, and what is its shape?",
     "reason": "The reference cluster has to be found first.",
     "mentions": [{"text": "Actinomycetota", "role": "condition"}],
     "target": ["feature_number"], "measure": ["pattern"]},
    {"question": "Which other clusters have a similar shape to that cluster?",
     "reason": "Every other curve is compared with the reference.", "uses": 1,
     "target": ["given", "pattern"], "measure": ["pattern"], "compare": "curves"},
]).model_dump()


def plans(similar_step):
    return Plans(plans=[
        {"steps": [{"kind": "feature_number", "top_n": 1}], "descriptor": {"pattern": True}},
        {"steps": [{"kind": "given"}, similar_step], "descriptor": {"pattern": True}},
    ], display={"needs_focus": True, "network_area": False, "grouping": "together", "reason": "r"}).model_dump()


SIMILAR = {"kind": "pattern", "criterion": "compare", "tool": "similar", "between": "clusters"}


def run(monkeypatch, similar_step, parse=PARSE, subs=SUBS, plan=None):
    asked = {}

    def ask(schema, system, user, site, reasoning=True):
        asked[site] = (system, user)
        return {"parse": parse, "breakdown": subs, "plan": plan or plans(similar_step)}[site]

    def judge(schema, card, state, user, force_reasoning=False):
        wanted = ([int(x) for x in user.rsplit("slot(s) ", 1)[1].rstrip(".").split(", ")]
                  if "Write only" in user else range(1, 50))
        return {"texts": [{"slot": i, "text": f"text {i}"} for i in wanted]}

    monkeypatch.setattr(frame, "_ask", ask)
    monkeypatch.setattr(nodes, "_judge", judge)
    events = []
    out = graph.answer(QUESTION, on_event=events.append)
    return out, asked, events


def commands(steps):
    return [s["command"] for s in steps if s["kind"] == "dashboard"]


def test_multi_step_question_is_answered_in_two_units(monkeypatch):
    out, asked, events = run(monkeypatch, SIMILAR)
    steps, trace = out["steps"], out["trace"]
    assert trace["N2"] == "multi_step" and trace["leaf"] == "L7" and len(trace["sub_claims"]) == 2
    # breakdown is told the kind and reads the templates; plan is told where step 2 starts
    assert asked["breakdown"][1].startswith("KIND: multi_step") and "find, then relate" in asked["breakdown"][0]
    assert "Starts from the clusters found by [1]" in asked["plan"][1]

    heads = [s for s in steps if s["kind"] == "unit"]
    assert [h["of"] for h in heads] == [2, 2]
    # the second step names the cluster the first one found
    assert heads[1]["question"] == "Which other clusters have a similar shape to Group_5?"
    assert heads[0]["overview"] == ("First set filter 1 to Actinomycetota, then brush Group_5 "
                                    "(top 1 by feature count).")
    # the question does not say in which sample group: the default is used and stated
    assert len(heads[1]["assumed"]) == 1 and "every sample group (A and C)" in heads[1]["assumed"][0]
    assert heads[0]["assumed"] == []

    cmds = commands(steps)
    assert cmds[:3] == ["set filter1:Actinomycetota", "brush node:Group_5", "set filter1:all"]
    assert "brush node:Group_3" in cmds
    assert not any("Group_2" in c for c in cmds)          # a network neighbour, not a similar curve
    # the client gets the plan first, then the playback with its units
    kinds = [e["event"] for e in events]
    assert kinds.index("plan") < kinds.index("steps") and kinds[-1] == "done"
    plan = next(e for e in events if e["event"] == "plan")
    assert plan["text"].startswith("This takes 2 steps:")
    last = [s for s in steps if s["kind"] == "message"][-1]
    assert last["role"] == "conclusion" and last["unit"] is None and last["text"]


def test_named_sample_group_leaves_nothing_to_assume(monkeypatch):
    out, _, _ = run(monkeypatch, {**SIMILAR, "a": {"subject": "A"}})
    heads = [s for s in out["steps"] if s["kind"] == "unit"]
    assert heads[1]["assumed"] == []
    assert heads[1]["overview"] == "First clear filter 1, then brush Group_3 (similar to Group_5 in A)."


def test_match_from_the_question_is_used(monkeypatch):
    out, _, _ = run(monkeypatch, {**SIMILAR, "match": "any"})
    heads = [s for s in out["steps"] if s["kind"] == "unit"]
    assert heads[1]["assumed"] == []
    shown = [c for c in commands(out["steps"]) if c.startswith(("brush node:", "select node:"))][1]
    assert shown.split(":")[1].split(",") == ["Group_3", "Group_6", "Group_7", "Group_9"]


def test_a_step_with_nothing_to_start_from_says_so(monkeypatch):
    subs = SubFrames(**SUBS).model_dump()
    subs["sub_frames"][0]["mentions"] = []                 # no filter: step 1 reads all clusters
    subs["sub_frames"][0]["target"] = ["all"]
    plan = plans(SIMILAR)
    plan["plans"][0]["steps"] = [{"kind": "all"}]
    out, _, _ = run(monkeypatch, SIMILAR, subs=subs, plan=plan)
    heads = [s for s in out["steps"] if s["kind"] == "unit"]
    assert heads[1]["assumed"] == ["Step 1 picked no cluster, so this step has nothing to start from."]


def test_direct_question_is_one_unit_and_skips_breakdown(monkeypatch):
    parse = Frame(kind="data", shape="direct", reason="a lookup",
                  mentions=[{"text": "Actinomycetota", "role": "condition"}],
                  target=["feature_number"], measure=["pattern"]).model_dump()
    asked = {}

    def ask(schema, system, user, site, reasoning=True):
        asked[site] = user
        one = plans(SIMILAR)
        one["plans"] = one["plans"][:1]
        return {"parse": parse, "plan": one}[site]        # KeyError if breakdown is called

    monkeypatch.setattr(frame, "_ask", ask)
    monkeypatch.setattr(nodes, "_judge", lambda *a, **k: {"texts": [{"slot": 1, "text": "t"}]})
    out = graph.answer("For Actinomycetota, which cluster has the most features?")
    heads = [s for s in out["steps"] if s["kind"] == "unit"]
    assert "breakdown" not in asked and len(heads) == 1 and heads[0]["of"] == 1
    assert out["trace"]["N2"] == "direct"


def test_a_split_that_loses_its_first_step_falls_back_to_one_pass(monkeypatch):
    """Step 1 names something that is not in the data, so step 2 has nothing to start from."""
    subs = SubFrames(**SUBS).model_dump()
    subs["sub_frames"][0]["mentions"] = [{"text": "Nosuchphylum", "role": "condition"}]
    one = plans(SIMILAR)
    one["plans"] = one["plans"][:1]
    out, asked, _ = run(monkeypatch, SIMILAR, subs=subs, plan=one)
    heads = [s for s in out["steps"] if s["kind"] == "unit"]
    assert len(heads) == 1 and heads[0]["of"] == 1 and heads[0]["question"] == QUESTION
    assert out["trace"]["N2"] == "direct" and "Starts from" not in asked["plan"][1]


def test_a_compared_sample_group_does_not_drop_the_step(monkeypatch):
    """ "in either cheese": A and C are found in the data but set no filter; the step stays."""
    subs = SubFrames(**SUBS).model_dump()
    subs["sub_frames"][1]["mentions"] = [{"text": "A", "role": "compare"}, {"text": "C", "role": "compare"}]
    out, _, _ = run(monkeypatch, {**SIMILAR, "match": "any"}, subs=subs)
    assert [s["of"] for s in out["steps"] if s["kind"] == "unit"] == [2, 2]


# ---- ids the model writes from memory for a function named in words --------------------------

def ask_ids(monkeypatch, ids):
    """Answer "where do the Type IV secretion genes fall" with the model giving `ids` from memory."""
    parse = Frame(kind="data", shape="direct", reason="a lookup", target=["feature_lookup"],
                  outside_concept="Type IV secretion", outside_ids=ids).model_dump()
    plan = Plans(plans=[{"steps": [{"kind": "feature_lookup"}], "descriptor": {}}],
                 display={"needs_focus": False, "network_area": False, "grouping": "together",
                          "reason": "r"}).model_dump()
    asked, wrote = {}, []

    def ask(schema, system, user, site, reasoning=True):
        asked[site] = user
        return {"parse": parse, "plan": plan}[site]

    def judge(schema, card, state, user, **kw):
        wrote.append(user)
        return {"texts": [{"slot": i, "text": "t"} for i in range(1, 9)]}

    monkeypatch.setattr(frame, "_ask", ask)
    monkeypatch.setattr(nodes, "_judge", judge)
    return graph.answer("Where do the Type IV secretion genes (KEGG) fall?"), asked, wrote


def test_ids_from_memory_are_used_and_flagged_before_the_actions(monkeypatch):
    out, _, wrote = ask_ids(monkeypatch, ["K03196", "K03197", "K99999"])
    head = next(s for s in out["steps"] if s["kind"] == "unit")
    note = head["assumed"][0]
    assert note.startswith('"Type IV secretion" was turned into KEGG ortholog ids from the model\'s memory')
    assert "K03196, K03197, K99999. 2 of 3 are in the data (not in the data: K99999)" in note
    assert "check it, or ask again with the ids themselves" in note
    kinds = [s["kind"] for s in out["steps"]]
    assert kinds.index("unit") < kinds.index("dashboard")          # said before anything is played
    search = next(s for s in out["steps"] if s["kind"] == "data" and s.get("op") == "llm_search")
    assert any(line.startswith("in the data: K03196 (") and "not in the data: K99999" in line
               for line in search["findings"])
    assert "from model knowledge, not looked up" in "\n".join(wrote)   # the writer is told too
    assert out["trace"]["leaf"] != "L2"


@pytest.mark.parametrize("ids, said", [
    ([], "I cannot list its KEGG ortholog ids reliably from memory"),
    (["K99998", "K99999"], "K99998, K99999. None of them is in the data"),
])
def test_without_a_usable_id_the_agent_stops_and_asks(monkeypatch, ids, said):
    out, asked, wrote = ask_ids(monkeypatch, ids)
    assert "plan" not in asked and out["trace"]["leaf"] == "L2"
    assert not [s for s in out["steps"] if s["kind"] in ("dashboard", "data")]
    slot = "\n".join(wrote)                      # what the writer of the one message is given
    assert said in slot and "Give the ids you mean" in slot and "ask for the ids" in slot


def test_ids_the_user_wrote_are_not_called_memory(monkeypatch):
    parse = Frame(kind="data", shape="direct", reason="a lookup", target=["feature_lookup"],
                  mentions=[{"text": "K03196", "role": "condition"}]).model_dump()
    plan = Plans(plans=[{"steps": [{"kind": "feature_lookup"}], "descriptor": {}}],
                 display={"needs_focus": False, "network_area": False, "grouping": "together",
                          "reason": "r"}).model_dump()
    monkeypatch.setattr(frame, "_ask", lambda schema, system, user, site, reasoning=True: {"parse": parse, "plan": plan}[site])
    monkeypatch.setattr(nodes, "_judge", lambda *a, **k: {"texts": [{"slot": 1, "text": "t"}]})
    out = graph.answer("Which contigs carry K03196?")
    assert not next(s for s in out["steps"] if s["kind"] == "unit")["assumed"]
    assert not [s for s in out["steps"] if s["kind"] == "data" and s.get("op") == "llm_search"]


def test_a_family_read_as_an_annotation_column_is_not_answered_as_any_annotation(monkeypatch):
    # "the Type IV secretion genes (KEGG)" read as "features with a KEGG annotation"
    parse = Frame(kind="data", shape="direct", reason="a lookup", target=["feature_number"], measure=["level3"],
                  mentions=[{"text": "Type IV secretion genes", "role": "condition"},
                            {"text": "KEGG annotations", "role": "condition"}]).model_dump()
    asked, wrote = {}, []
    monkeypatch.setattr(frame, "_ask", lambda schema, system, user, site, reasoning=True: asked.setdefault(site, parse))
    monkeypatch.setattr(nodes, "_judge", lambda schema, card, state, user, **kw: wrote.append(user) or {"texts": [{"slot": 1, "text": "t"}]})
    out = graph.answer("Where do the Type IV secretion genes (KEGG) fall?")
    assert list(asked) == ["parse"] and out["trace"]["leaf"] == "L2"
    assert '\\"Type IV secretion genes\\" is not a value or an id in the data' in "\n".join(wrote) \
        or '"Type IV secretion genes" is not a value or an id in the data' in "\n".join(wrote)
    assert "KEGG ortholog ids" in "\n".join(wrote)


def test_a_split_cannot_drop_the_named_family_or_go_on_without_ids(monkeypatch):
    parse = Frame(kind="data", shape="multi_step", reason="two things", target=["feature_lookup"],
                  outside_concept="Type IV secretion", outside_ids=["K03196", "K03197"]).model_dump()
    lost = SubFrames(sub_frames=[
        {"question": "Which clusters hold features with KEGG annotations?", "reason": "r",
         "mentions": [{"text": "KEGG annotations", "role": "condition"}], "target": ["feature_number"]},
        {"question": "Do those clusters share one cluster?", "reason": "r", "uses": 1, "target": ["given"]},
    ]).model_dump()
    plan = Plans(plans=[{"steps": [{"kind": "feature_lookup"}], "descriptor": {}}],
                 display={"needs_focus": False, "network_area": False, "grouping": "together", "reason": "r"}).model_dump()
    monkeypatch.setattr(nodes, "_judge", lambda *a, **k: {"texts": [{"slot": i, "text": "t"} for i in range(1, 9)]})
    monkeypatch.setattr(frame, "_ask", lambda schema, system, user, site, reasoning=True:
                        {"parse": parse, "breakdown": lost, "plan": plan}[site])
    out = graph.answer("Where do the Type IV secretion genes (KEGG) fall, and do they share one cluster?")
    heads = [s for s in out["steps"] if s["kind"] == "unit"]
    assert len(heads) == 1 and "from the model\'s memory" in heads[0]["assumed"][0]     # one direct pass
    assert "search table:K03196,K03197" in [s.get("command") for s in out["steps"]]

    no_ids = SubFrames(sub_frames=[
        {"question": "Where do the Type IV secretion genes fall?", "reason": "r", "target": ["feature_lookup"],
         "outside_concept": "Type IV secretion", "outside_ids": ["K99999"]},
        {"question": "Are those clusters connected?", "reason": "r", "uses": 1, "target": ["given", "network"]},
    ]).model_dump()
    monkeypatch.setattr(frame, "_ask", lambda schema, system, user, site, reasoning=True:
                        {"parse": parse, "breakdown": no_ids}[site])     # KeyError if plan is called
    out = graph.answer("Where do the Type IV secretion genes (KEGG) fall, and are those clusters connected?")
    assert out["trace"]["leaf"] == "L2" and not [s for s in out["steps"] if s["kind"] == "dashboard"]


def test_a_loose_word_next_to_a_level_value_does_not_stop_the_answer():
    from agent.core.dataset import load_dataset
    ds = load_dataset()
    fr = Frame(kind="data", shape="direct", reason="r", target=["feature_number"], measure=["level3"],
               mentions=[{"text": "Actinomycetota", "role": "condition"},
                         {"text": "molecular function", "role": "condition"},
                         {"text": "KEGG ortholog", "role": "measure"}]).model_dump()
    _, f, _ = frame.resolve(fr, ds)
    assert f["external_concept"] is None and f["level1"] == ["Actinomycetota"]
    assert frame._ids_stop(f, "q", ds) is None


# ---- what a part knows about itself (modules/<part>/method.md) -------------------------------

def network_answer(monkeypatch, texts, kind="network"):
    """A direct question answered through the network (or by cluster size); `texts` are what the
    stubbed writer returns on its first, second ... call."""
    parse = Frame(kind="data", shape="direct", reason="a lookup", target=[kind]).model_dump()
    step = {"kind": "network", "criterion": "strongest_edge"} if kind == "network" else {"kind": "feature_number", "top_n": 1}
    plan = Plans(plans=[{"steps": [step], "descriptor": {}}],
                 display={"needs_focus": True, "network_area": True, "grouping": "together", "reason": "r"}).model_dump()
    calls = []

    def judge(schema, card, state, user, **kw):
        calls.append({"card": card, "user": user})
        return {"texts": [{"slot": 1, "text": texts[min(len(calls), len(texts)) - 1]}]}

    monkeypatch.setattr(frame, "_ask", lambda schema, system, user, site, reasoning=True: {"parse": parse, "plan": plan}[site])
    monkeypatch.setattr(nodes, "_judge", judge)
    return graph.answer("Which two clusters share the strongest edge?"), calls


def test_writer_gets_the_notes_of_the_part_its_findings_come_from(monkeypatch):
    out, calls = network_answer(monkeypatch, ["Group_1 and Group_2 are linked."])
    assert len(calls) == 1 and "WHAT THE NETWORK CAN SUPPORT" in calls[0]["card"]
    assert "the weight is a ranking, not a test" in calls[0]["card"]
    out, calls = network_answer(monkeypatch, ["Group_10 is the largest."], kind="feature_number")
    assert "WHAT THE NETWORK CAN SUPPORT" not in calls[0]["card"]       # no network finding, no notes


def test_a_message_that_claims_a_cause_is_written_once_more(monkeypatch):
    out, calls = network_answer(monkeypatch, ["Group_1 drives Group_2, a significant link.",
                                              "Group_1 and Group_2 are linked."])
    assert len(calls) == 2 and "REWRITE: Slot 1 used 'drives', 'significant'" in calls[1]["user"]
    assert [s["text"] for s in out["steps"] if s["kind"] == "message"] == ["Group_1 and Group_2 are linked."]


def test_a_question_about_the_method_is_answered_from_the_reference(monkeypatch):
    parse = Frame(kind="method", part="network", reason="asks what an edge means").model_dump()
    asked, wrote = {}, []
    monkeypatch.setattr(frame, "_ask", lambda schema, system, user, site, reasoning=True: asked.setdefault(site, parse))
    monkeypatch.setattr(nodes, "_judge", lambda schema, card, state, user, **kw: wrote.append(user) or {"texts": [{"slot": 1, "text": "t"}]})
    out = graph.answer("Does a link mean one cluster causes the other?")
    assert list(asked) == ["parse"] and out["trace"]["leaf"] == "LM"
    assert [s["kind"] for s in out["steps"]] == ["message"]
    assert "GENIE3" in wrote[0] and "What the results can support" in wrote[0]

    parse["part"] = "clusters"                                        # no file: the manifest's method
    asked.clear(), wrote.clear()
    graph.answer("How were the clusters made?")
    assert "k-means" in wrote[0].lower() and "GENIE3" not in wrote[0]


def test_denying_a_cause_is_not_a_claim(monkeypatch):
    pattern = __import__("agent.core.module", fromlist=["x"]).by_name("network").avoid()
    assert nodes._claimed(pattern, "Group_1 drives Group_2. The link is significant.") == ["drives", "significant"]
    assert nodes._claimed(pattern, "They are linked; this does not mean that one causes the other.") == []
    assert nodes._claimed(pattern, "The weight is a ranking, not a test of significance. Group_1 regulates it.") == ["regulates"]
    out, calls = network_answer(monkeypatch, ["Group_1 and Group_2 are linked, which is no proof that one causes the other."])
    assert len(calls) == 1                                           # nothing to rewrite


def test_the_writer_prompt_names_no_cluster_or_value_of_the_data():
    from agent.core import prompts
    from agent.core.dataset import load_dataset
    ds = load_dataset()
    text = prompts.for_data(prompts.COMPOSE, ds)
    assert not [c for c in ds.clusters if c in text]
    assert not [v for v in list(ds.level1_values) + list(ds.level2_values) if v != "Unknown" and v in text]
