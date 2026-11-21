"""The frame pipeline (AGENT_PIPELINE=frame): parse -> resolve -> plan -> run -> compose.

    START -> parse -> leaf_L0 | leaf_L1 | leaf_L2 | breakdown | plan
    breakdown -> plan -> run_frame -> leaf_frame -> compose_messages -> END

breakdown runs only for a question that parse marks as multi_step (one lookup needs the answer
of another) or evidence_chain (a hypothesis). It splits the question into sub-questions; each
becomes one unit of the answer, and one may start from the clusters an earlier one found.

parse fills the roles of the question in one LLM call (K=N0, R=N1, H=N2, mentions, A/E targets,
B measures, D comparison). Code looks every mention up in the data and builds the N3 filters.
plan fills N4 + N5 for each (sub-)question and N6 once, reading only the skill cards the roles
ask for. The state keeps the tree's field names, so answer()'s trace and eval_trace.py read the
same N0..N6 as with the tree pipeline.
"""

import json
import re
import time
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from . import keywords as kw
from . import leaves, prompts, skills
from .data_tools import load_dataset
from .nodes import (MAX_SUB_CLAIMS, AgentState, _debug, _emit, _filled, _route, clean_filters,
                    compose_messages, leaf_L0, leaf_L1, leaf_L2, log_unit, run_unit)
from .schemas import Frame, Plans, SubFrames


SPLIT = ("multi_step", "evidence_chain")   # shapes that go through breakdown


class FrameState(AgentState, total=False):
    frames: list        # roles of each (sub-)question
    plans: list
    skills: list


def _ask(schema, system, user, site, reasoning=True):
    from .llm import JUDGE_TIER, ask

    t0 = time.time()
    out = ask(schema, system, user, reasoning=reasoning and JUDGE_TIER == "reasoning", site=site)
    _debug("  llm", f"{site}, {time.time() - t0:.1f}s")
    return out.model_dump()


# ---- resolve: code only ----------------------------------------------------

def _column_of(text, ds):
    """An annotation column named in words ('KEGG annotations' -> KEGG_ID); None otherwise."""
    low = str(text).lower()
    for col in ds.cfg.level3:
        if col == ds.cfg.id_col:
            continue
        stem = re.sub(r"[_\s-]*id$", "", col.lower())
        if stem and re.search(rf"\b{re.escape(stem)}\b", low):
            return col
    return None


def _outside_column(ids, ds):
    """The level-3 column the outside ids belong to: the one they are found in, else by their form."""
    for i in ids:
        hits = kw._level3_hits(i, ds)
        if hits:
            return hits[0]["column"]
    # the column notes give an example id ("KEGG ortholog ids such as K03196"): match its prefix
    for col, note in zip(ds.cfg.level3, ds.cfg.level3_notes):
        example = re.search(r"\b([A-Za-z]+:?)\d+", note)
        if col != ds.cfg.id_col and example and any(str(i).upper().startswith(example.group(1).upper())
                                                    for i in ids):
            return col
    return next((c for c in ds.cfg.level3 if c != ds.cfg.id_col), None)


def resolve(frame, ds):
    """Look the mentions of one frame up in the data. Returns (keyword map, N3 filters, resolved roles)."""
    mentions = frame.get("mentions") or []
    kmap = kw.map_keywords([m["text"] for m in mentions], ds)
    by_word = {k["keyword"]: k for k in kmap["keywords"]}
    f = {"cols": None, "level1": [], "level2": [], "level3_column": None, "level3_values": [],
         "level3_has_annotation": False, "external_concept": None, "contrast": "none"}
    subjects, roles = [], []

    def add(slot, value):
        if value not in f[slot]:
            f[slot].append(value)

    level_contrast = frame.get("compare") in ("level1", "level2", "with_and_without_level2")
    for m in mentions:
        matches = (by_word.get(str(m["text"]).strip()) or {"matches": []})["matches"]
        if any(x.get("match", "exact") == "exact" for x in matches):
            # 'Actinomycetota' is the phylum; its close spelling 'Actinomycetes' (a class) is not meant
            matches = [x for x in matches if x.get("match", "exact") == "exact"]
        found = [f"{x['level']}={x['value']}" + (" [close spelling]" if x.get("match") == "close spelling" else "")
                 for x in matches]
        col = _column_of(m["text"], ds) if not matches else None
        if col:
            found.append(f"level3 column={col}")
        roles.append(f"{m['text']} ({m['role']}): " + (", ".join(found) or "not in the data"))
        # a measured or target term never becomes a filter; a compared one only when level values
        # are compared (two sample groups or two curves are read by the plan, not filtered)
        if m["role"] == "condition" or (m["role"] == "compare" and level_contrast):
            pass
        elif m["role"] == "compare":
            subjects += [(x["value"], "compare") for x in matches if x["level"] == "sample_group"]
            continue
        else:
            continue
        for x in matches:
            if x["level"] in ("level1", "level2"):
                add(x["level"], x["value"])
            elif x["level"] == "level3":
                f["level3_column"] = f["level3_column"] or x["column"]
                if x["column"] == f["level3_column"]:
                    add("level3_values", x["value"])
            elif x["level"] == "sample_group":
                subjects.append((x["value"], m["role"]))
        if col and not f["level3_column"]:
            f["level3_column"], f["level3_has_annotation"] = col, True

    if frame.get("outside_concept"):
        f["external_concept"] = frame["outside_concept"]
        ids = [str(i).strip() for i in frame.get("outside_ids") or [] if str(i).strip()]
        if ids:
            f["level3_column"] = f["level3_column"] or _outside_column(ids, ds)
            for i in ids:
                add("level3_values", i)
    if f["level3_values"]:
        f["level3_has_annotation"] = False
    conditions = [s for s, role in subjects if role == "condition"]
    if len(set(conditions)) == 1 and frame.get("compare") != "curves":
        f["cols"] = conditions[0]
    if frame.get("compare") in ("level1", "level2", "with_and_without_level2"):
        f["contrast"] = frame["compare"]
    f, dropped = clean_filters(f, ds)
    for level in ("level1", "level2"):   # one value has nothing to be set against
        if f["contrast"] == level and len(f[level]) < 2:
            f["contrast"] = "none"
    for d in dropped:
        kmap["notes"].append(f"ignored, not in the data: {d}")
    return kmap, f, roles


def _merge_kmaps(maps):
    out = {"keywords": [], "notes": []}
    seen = set()
    for m in maps:
        for k in m["keywords"]:
            if k["keyword"] not in seen:
                seen.add(k["keyword"])
                out["keywords"].append(k)
        out["notes"] += [n for n in m["notes"] if n not in out["notes"]]
    return out


# ---- nodes -----------------------------------------------------------------

def parse(state: FrameState):
    _debug("question", state["question"])
    ds = load_dataset()
    out = _ask(Frame, prompts.PARSE + "\n\n" + prompts.parse_context(ds), state["question"], "parse")
    _debug("parse K/R/H", f"{out['kind']} / {out['status']} / {out['shape']}: {out['reason']}"
           + (f"   control={out['control']}, value={out['value']}" if out["kind"] == "design" else ""))
    kmap, filters, roles = resolve(out, ds)
    for line in roles:
        _debug("parse mention", line)
    _debug("parse roles", f"target={out['target']} measure={out['measure']} compare={out['compare']}"
           + (f" outside={out['outside_concept']} {out['outside_ids']}" if out["outside_concept"] else ""))
    frame = {**out, "question": state["question"], "filters": filters, "roles": roles}
    if out["kind"] == "data" and out["status"] != "ask":
        split = out["shape"] in SPLIT
        _emit("status", text="Splitting the question into steps" if split else "Planning what to look at")
    notes = [out["note"]] if out["status"] == "assume_default" and out["note"] else []
    return {
        "keyword_map": kmap,
        "kind": {k: out[k] for k in ("kind", "control", "value", "reason")},
        "completeness": {"status": out["status"], "note": out["note"]},
        "assumptions": notes,
        "shape": out["shape"],
        "frames": [frame],
        "sub_questions": [state["question"]],
        "idx": 0, "units": [],
    }


def route_parse(state: FrameState):
    kind, status, shape = state["kind"]["kind"], state["completeness"]["status"], state["shape"]
    if kind == "out_of_scope":
        return _route("parse route", "leaf_L0", "kind is out_of_scope")
    if kind == "design":
        return _route("parse route", "leaf_L1", "kind is design")
    if status == "ask":
        return _route("parse route", "leaf_L2", "status is ask")
    return _route("parse route", "breakdown" if shape in SPLIT else "plan", f"shape is {shape}")


def breakdown(state: FrameState):
    """An independent LLM splits the question into direct sub-questions with their roles filled.

    A hypothesis (evidence_chain) becomes the steps of an argument; a question that needs one
    lookup before the next (multi_step) becomes those lookups. A sub-question may start from the
    clusters an earlier one found (`uses`); the templates are in skills/breakdown.md.
    """
    ds = load_dataset()
    system = prompts.BREAKDOWN + "\n\n" + skills.card("breakdown") + "\n\n" + prompts.parse_context(ds)
    user = f"KIND: {state['shape']}\nQUESTION: {state['question']}"
    subs = _ask(SubFrames, system, user, "breakdown")["sub_frames"][:MAX_SUB_CLAIMS]
    frames, maps, notes = [], [state["keyword_map"]], []
    kept = {}   # number of a sub-question as the LLM wrote it -> its number among the kept ones
    for n, sub in enumerate(subs, 1):
        kmap, filters, roles = resolve(sub, ds)
        # dropped when none of its conditions names something in the data. A sample group that is
        # compared ("in either cheese") is found in the data without becoming a filter.
        tried = [line for m, line in zip(sub.get("mentions") or [], roles)
                 if m["role"] in ("condition", "compare")]
        if tried and all(line.endswith("not in the data") for line in tried) and not sub.get("uses"):
            notes.append(f"sub-question dropped, its conditions are not in the data: {sub['question']}")
            _debug("breakdown", f"dropped: {sub['question']}")
            continue
        if sub.get("uses") and sub["uses"] not in kept:
            # it starts from the clusters of a sub-question that is not there: nothing to start from
            _debug("breakdown", f"dropped, the step it starts from is missing: {sub['question']}")
            continue
        sub = {**sub, "uses": kept.get(sub.get("uses"))}
        kept[n] = len(frames) + 1
        frames.append({**sub, "filters": filters, "roles": roles})
        # the words of a sub-question are the breakdown's, not the user's: a word of it that is
        # not a data value is no assumption about the question, so it is not reported
        maps.append({**kmap, "notes": [n for n in kmap["notes"] if " is not a " not in n]})
    if not frames or (state["shape"] == "multi_step" and len(frames) < len(subs)):
        # nothing testable, or a step of the lookup is missing: half an answer would look like a
        # whole one, so the question is answered as one direct pass
        frames = state["frames"]
    for i, fr in enumerate(frames, 1):
        _debug("breakdown", f"{i}/{len(frames)} {fr['question']}"
               + (f"   uses {fr['uses']}" if fr.get("uses") else "")
               + (f"   because: {fr['reason']}" if fr.get("reason") else ""))
        for line in fr["roles"]:
            _debug("  mention", line)
    if len(frames) > 1:
        lead = "This needs an argument in " if state["shape"] == "evidence_chain" else "This takes "
        _emit("plan", text=lead + str(len(frames)) + " steps:\n"
              + "\n".join(f"{i}. {fr['question']}" for i, fr in enumerate(frames, 1)))
        _emit("status", text="Planning what to look at")
    kmap = _merge_kmaps(maps)
    kmap["notes"] += notes
    out = {"frames": frames, "sub_questions": [fr["question"] for fr in frames], "keyword_map": kmap}
    if len(frames) == 1:
        out["shape"] = "direct"   # answered in one pass after all; the trace says how it was answered
    return out


def _frame_text(i, fr, later=()):
    """`later`: the numbers of the sub-questions that start from the clusters this one finds."""
    roles = {k: fr.get(k) for k in ("target", "measure", "compare") if fr.get(k) not in (None, [], "none")}
    return (f"[{i}] Question: {fr['question']}\n"
            f"    Roles: {json.dumps(roles)}\n"
            f"    Mentions: {'; '.join(fr['roles']) or '(none)'}\n"
            f"    Filters already set (N3): {_filled(fr['filters'])}"
            + (f"\n    Starts from the clusters found by [{fr['uses']}]: the first step is kind=given "
               "with no cluster names (code fills them in), then the step that works on them."
               if fr.get("uses") else "")
            + (f"\n    Its clusters are the starting point of [{', '.join(map(str, later))}]: plan only "
               "what this question asks; the step that works on them belongs there." if later else ""))


def plan(state: FrameState):
    ds = load_dataset()
    frames, status = state["frames"], state["completeness"]["status"]
    names = skills.pick_skills(frames, status, state.get("keyword_map"))
    _debug("plan skills", ", ".join(names) or "(core only)")
    system = skills.plan_prompt(names) + "\n\n" + prompts.plan_context(ds, state["dash_state"], status)
    user = "\n".join(_frame_text(i, fr, [k for k, x in enumerate(frames, 1) if x.get("uses") == i])
                     for i, fr in enumerate(frames, 1))
    if status == "use_current_selection":
        user += "\nThe question refers to the clusters selected now: use kind=given."
    if len(frames) > 1:
        user += f"\nOriginal question: {state['question']}\nGive exactly {len(frames)} plans, one per question."
    out = _ask(Plans, system, user, "plan")
    plans = out["plans"][:len(frames)]
    if len(plans) < len(frames):
        _debug("plan", f"got {len(plans)} plan(s) for {len(frames)} question(s); the rest read all clusters")
        plans += [{"steps": [{"kind": "all"}], "descriptor": {}}] * (len(frames) - len(plans))
    for i, p in enumerate(plans, 1):
        for j, st in enumerate(p["steps"], 1):
            _debug("plan N4", f"[{i}] step {j}: {_filled(st)}")
        _debug("plan N5", f"[{i}] {_filled(p['descriptor'])}")
    d = out["display"]
    _debug("plan N6", f"needs_focus={d['needs_focus']}, network_area={d['network_area']}, "
           f"grouping={d['grouping']}: {d['reason']}")
    _emit("status", text="Reading the data")
    return {"plans": plans, "display": d, "skills": names}


THOSE = re.compile(r"\b(?:that|those|the same|these|this) clusters?\b", re.I)


def _from_earlier(fr, steps, units):
    """A sub-question that `uses` an earlier one: its question and steps with those clusters named.

    Returns (question, steps, note). The first `given` step gets the clusters the earlier unit
    picked (one is put in front when the plan has none). When the earlier unit picked nothing
    there is nothing to start from: the steps are dropped and `note` says so.
    """
    n = fr["uses"]
    base = []
    for run in units[n - 1]["runs"]:
        base += [c for c in run["targets"] if c not in base]
    picked = len(base) < len(load_dataset().clusters)   # "all clusters" is not a pick
    if not base or not picked:
        return fr["question"], [{"kind": "all"}], f"Step {n} picked no cluster, so this step has nothing to start from."
    steps = [dict(st) for st in steps]
    given = next((st for st in steps if st["kind"] == "given"), None)
    if given is None:
        given = {"kind": "given"}
        steps.insert(0, given)
    given["clusters"] = list(base)
    names = ", ".join(base)
    question = THOSE.sub(names, fr["question"]) if THOSE.search(fr["question"]) \
        else f"{fr['question'].rstrip()} (starting from {names})"
    return question, steps, None


def run_frame(state: FrameState):
    units = []
    for i, (fr, p) in enumerate(zip(state["frames"], state["plans"])):
        if len(state["frames"]) > 1:
            _debug("sub-question", f"{i + 1}/{len(state['frames'])} {fr['question']}")
        question, steps, note = fr["question"], p["steps"], None
        if fr.get("uses") and fr["uses"] <= len(units):
            question, steps, note = _from_earlier(fr, steps, units)
        unit = run_unit(question, fr["filters"], {"steps": steps}, p["descriptor"] if not note else {},
                        state["dash_state"])
        if note:
            unit["assumed"].append({"field": "uses", "used": None, "options": [], "text": note})
        if len(state["frames"]) > 1:
            unit["reason"] = fr.get("reason") or ""
        log_unit(unit)
        units.append(unit)
    return {"units": units, "idx": len(units)}


def leaf_frame(state: FrameState):
    units, display = state["units"], state["display"]
    leaf = leaves.choose_leaf(units, display)
    _debug("leaf", f"{leaf}   (computed from the plan's display, {len(units)} sub-question(s))")
    return {"leaf": leaf, "steps": leaves.assemble(leaf, units, display, state.get("shape") or "evidence_chain")}


@lru_cache(maxsize=1)
def build_frame_graph():
    g = StateGraph(FrameState)
    for name, fn in (("parse", parse), ("breakdown", breakdown), ("plan", plan), ("run_frame", run_frame),
                     ("leaf_frame", leaf_frame), ("leaf_L0", leaf_L0), ("leaf_L1", leaf_L1),
                     ("leaf_L2", leaf_L2), ("compose_messages", compose_messages)):
        g.add_node(name, fn)
    g.add_edge(START, "parse")
    g.add_conditional_edges("parse", route_parse, ["leaf_L0", "leaf_L1", "leaf_L2", "breakdown", "plan"])
    g.add_edge("breakdown", "plan")
    g.add_edge("plan", "run_frame")
    g.add_edge("run_frame", "leaf_frame")
    for name in ("leaf_frame", "leaf_L0", "leaf_L1", "leaf_L2"):
        g.add_edge(name, "compose_messages")
    g.add_edge("compose_messages", END)
    return g.compile()
