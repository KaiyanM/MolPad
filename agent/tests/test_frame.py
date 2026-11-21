"""The frame pipeline from question to playback, with every LLM call stubbed. No API key."""

import pytest

from agent import frame, graph, nodes
from agent.schemas import Frame, Plans, SubFrames

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

    monkeypatch.setenv("AGENT_PIPELINE", "frame")
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

    monkeypatch.setenv("AGENT_PIPELINE", "frame")
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
