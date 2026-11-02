"""Graph nodes: one per node of the decision tree, plus the backend pass and the message writer."""

import json
import os
import re
import sys
import time
from typing import TypedDict

from . import keywords as kw
from . import leaves, prompts
from .data_tools import Session, load_dataset
from .schemas import (Completeness, Descriptor, Display, Filters, Keywords, Kind, Messages,
                      Selector, Shape, SubClaims)

# Set by AGENT_DEBUG=1, `python -m agent.run --debug` or answer(..., debug=True).
DEBUG = os.getenv("AGENT_DEBUG", "").strip() not in ("", "0")

MAX_SUB_CLAIMS = 4


class AgentState(TypedDict, total=False):
    question: str
    dash_state: dict        # level1, level2, scope, colour_by, min_weight, selected_clusters, layout
    keyword_map: dict       # keywords of the question and the level each belongs to
    kind: dict              # N0
    completeness: dict      # N1
    assumptions: list
    shape: str              # N2
    sub_questions: list
    idx: int                # sub-question being worked on
    filters: dict           # N3, current sub-question
    selector: dict          # N4
    descriptor: dict        # N5
    units: list             # one finished backend pass per sub-question
    display: dict           # N6
    leaf: str
    steps: list


def _debug(node, text):
    """One readable line per decision, on stderr so the JSON on stdout stays clean."""
    if DEBUG:
        print(f"[debug] {node:<16} {text}", file=sys.stderr, flush=True)


def _filled(d):
    """'key=value' for the slots that are set; '(nothing)' when none is."""
    parts = [f"{k}={json.dumps(v)}" for k, v in d.items() if v not in (None, [], "", False, "none")]
    return ", ".join(parts) or "(nothing)"


def _route(node, target, why=""):
    _debug(node, f"-> {target}" + (f"   ({why})" if why else ""))
    return target


# Words of a message that say something is missing from a cluster ("contains only Bacilli",
# "no Clostridia", "does not include", "100% Bacilli"). A filtered run cannot show that.
ABSENCE = re.compile(r"(?i:\bcontains? only\b|\bonly contains?\b|\bdoes(?: not|n't) (?:include|contain|have)\b"
                     r"|\blacks?\b|\b100 ?%)|\b[Nn]o [A-Z][a-z]+")   # "no Clostridia", not "no cluster"


def _compose_reasoning():
    return os.getenv("AGENT_COMPOSE_TIER", "basic").strip().lower() == "reasoning"


def _judge(schema, card, state, user, force_reasoning=False):
    from .llm import JUDGE_TIER, ask  # imported late: the rest of the module works without an API key

    ds = load_dataset()
    if schema is Messages:
        # the writer cites the findings only; the dataset block is just the background here
        system = card + "\n\nBACKGROUND\n" + ds.cfg.background
    else:
        system = card + "\n\n" + prompts.dataset_block(ds, state["dash_state"])
    # N1 judges the wording of the question only; a keyword that is not in the data is reported
    # in the message instead of stopping the run with a clarifying question.
    if state.get("keyword_map") and schema not in (Messages, Completeness):
        system += "\n\n" + prompts.keyword_block(kw.as_text(state["keyword_map"]))
    # the message writer uses the basic model unless AGENT_COMPOSE_TIER=reasoning
    if schema is Messages:
        reasoning = force_reasoning or _compose_reasoning()
    else:
        reasoning = JUDGE_TIER == "reasoning"
    t0 = time.time()
    out = ask(schema, system, user, reasoning=reasoning, site=schema.__name__).model_dump()
    _debug("  llm", f"{schema.__name__} by the {'reasoning' if reasoning else 'basic'} model, "
           f"{time.time() - t0:.1f}s")
    return out


def _current(state):
    return state["sub_questions"][state["idx"]]


# ---- keywords --------------------------------------------------------------

def keywords(state: AgentState):
    """Pick the keywords of the question (LLM), then look each one up in the data (no LLM)."""
    from .llm import JUDGE_TIER, ask

    _debug("question", state["question"])
    ds = load_dataset()
    vocab = kw.vocabulary(ds)
    _debug("vocabulary", f"level1 {vocab['level1']['name']} ({vocab['level1']['column']}): "
           + ", ".join(vocab["level1"]["values"]))
    _debug("vocabulary", f"level2 {vocab['level2']['name']} ({vocab['level2']['column']}): "
           + ", ".join(vocab["level2"]["values"]))
    system = prompts.KEYWORDS + "\n\nBACKGROUND\n" + ds.cfg.background
    t0 = time.time()
    words = ask(Keywords, system, state["question"], reasoning=JUDGE_TIER == "reasoning",
                site="keywords").keywords
    _debug("  llm", f"Keywords, {time.time() - t0:.1f}s: {words}")
    kmap = kw.map_keywords(words, ds)
    for line in kw.as_text(kmap).splitlines():
        _debug("keyword map", line[2:])
    return {"keyword_map": kmap}


# ---- N0 - N2 ---------------------------------------------------------------

def n0_kind(state: AgentState):
    out = _judge(Kind, prompts.N0, state, state["question"])
    _debug("N0 kind", f"{out['kind']}: {out['reason']}"
           + (f"   control={out['control']}, value={out['value']}" if out["kind"] == "design" else ""))
    return {"kind": out}


def route_n0(state: AgentState):
    kind = state["kind"]["kind"]
    target = {"out_of_scope": "leaf_L0", "design": "leaf_L1"}.get(kind, "n1_completeness")
    return _route("N0 route", target, f"kind is {kind}")


def n1_completeness(state: AgentState):
    out = _judge(Completeness, prompts.N1, state, state["question"])
    notes = [out["note"]] if out["status"] == "assume_default" and out["note"] else []
    _debug("N1 completeness", out["status"] + (f": {out['note']}" if out["note"] else ""))
    return {"completeness": out, "assumptions": notes}


def route_n1(state: AgentState):
    status = state["completeness"]["status"]
    return _route("N1 route", "leaf_L2" if status == "ask" else "n2_shape", f"status is {status}")


def n2_shape(state: AgentState):
    shape = _judge(Shape, prompts.N2, state, state["question"])["shape"]
    subs = [state["question"]]
    if shape == "evidence_chain":
        from .llm import ask

        system = prompts.N2_SPLIT + "\n\n" + prompts.dataset_block(load_dataset(), state["dash_state"])
        claims = ask(SubClaims, system, state["question"], reasoning=True, site="split").sub_claims
        subs = claims[:MAX_SUB_CLAIMS] or subs
    _debug("N2 shape", shape)
    if shape == "evidence_chain":
        for i, q in enumerate(subs, 1):
            _debug("N2 sub-claim", f"{i}/{len(subs)} {q}")
    return {"shape": shape, "sub_questions": subs, "idx": 0, "units": []}


# ---- N3 - N5 (slots) -------------------------------------------------------

def n3_filters(state: AgentState):
    if len(state["sub_questions"]) > 1:
        _debug("sub-question", f"{state['idx'] + 1}/{len(state['sub_questions'])} {_current(state)}")
    out = _judge(Filters, prompts.N3, state, _current(state))
    _debug("N3 filters", _filled(out))
    return {"filters": out}


def n4_selector(state: AgentState):
    user = f"Question: {_current(state)}\nFilter slots already filled: {json.dumps(state['filters'])}"
    if state["completeness"]["status"] == "use_current_selection":
        user += "\nThe question refers to the clusters selected now: use kind=given."
    out = _judge(Selector, prompts.N4, state, user)
    for i, st in enumerate(out["steps"], 1):
        _debug("N4 selector", f"step {i}: {_filled(st)}")
    if not out["steps"]:
        _debug("N4 selector", "(no step: all clusters)")
    return {"selector": out}


def n5_descriptor(state: AgentState):
    user = (f"Question: {_current(state)}\nFilter slots: {json.dumps(state['filters'])}\n"
            f"Selector: {json.dumps(state['selector'])}")
    out = _judge(Descriptor, prompts.N5, state, user)
    _debug("N5 descriptor", _filled(out))
    return {"descriptor": out}


# ---- backend pass ----------------------------------------------------------

def _match(value, valid):
    """Case-insensitive match of an LLM-written value against the valid ones."""
    low = {str(v).lower(): v for v in valid}
    return low.get(str(value).strip().lower())


def clean_filters(filters, ds):
    """Keep only values that exist in the data; report what was dropped."""
    f, dropped = dict(filters), []
    for slot, valid in (("level1", ds.level1_values), ("level2", ds.level2_values)):
        kept = []
        for v in f.get(slot) or []:
            m = _match(v, valid)
            (kept if m else dropped).append(m or f"{slot} '{v}'")
        f[slot] = kept
    if f.get("cols"):
        m = _match(f["cols"], ds.subjects) or _match(str(f["cols"]).split()[-1], ds.subjects)
        if not m:
            dropped.append(f"sample group '{f['cols']}'")
        f["cols"] = m
    if f.get("level3_column"):
        m = _match(f["level3_column"], ds.cfg.level3)
        if not m:
            dropped.append(f"level-3 column '{f['level3_column']}'")
        f["level3_column"] = m
    return f, dropped


def _variants(f):
    """(label, level1 value, level2 values) for each run of the filter."""
    l1 = f["level1"][0] if f["level1"] else None
    contrast = f.get("contrast", "none")
    if contrast == "level1" and len(f["level1"]) > 1:
        return [(v, v, f["level2"]) for v in f["level1"]]
    if contrast == "level2" and len(f["level2"]) > 1:
        # with several level-1 values, each class already implies its own: do not filter by the first
        return [(v, l1 if len(f["level1"]) < 2 else None, [v]) for v in f["level2"]]
    if contrast == "with_and_without_level2" and f["level2"]:
        return [(l1 or "all", l1, []), (" + ".join([l1 or "all"] + f["level2"]), l1, f["level2"])]
    return [(None, l1, f["level2"])]


def _slice(side, ds):
    """One side of a comparison as the LLM wrote it, with the sample group matched to the data."""
    side = {k: v for k, v in (side or {}).items() if v not in (None, "")}
    if "subject" in side:
        side["subject"] = _match(side["subject"], ds.subjects) or side["subject"]
    return side or None


def _threshold(text):
    if text in (None, "", "current"):
        return None
    try:
        return float(text)
    except ValueError:
        return str(text).lower()


def run_unit(question, filters, selector, descriptor, dash_state, ds=None):
    """Run the data actions for one (sub-)question. Returns the unit used by the leaf templates."""
    ds = ds or load_dataset()
    f, dropped = clean_filters(filters, ds)
    l3col = f.get("level3_column")
    l3vals = f.get("level3_values") or []
    runs = []
    contrast_l1 = f.get("contrast") == "level1" and len(f["level1"]) > 1
    contrast_l2 = f.get("contrast") == "level2" and len(f["level2"]) > 1

    for label, level1, level2 in _variants(f):
        s = Session(ds, dash_state)
        steps = []

        def do(action, op, **args):
            args = {k: v for k, v in args.items() if v not in (None, [], False)}
            result = s.run(op, **args)
            steps.append(leaves.data_step(action, op, args, result))
            return result

        if f.get("external_concept") and l3vals:
            steps.append(leaves.data_step(f"llm: search {f['external_concept']}", "llm_search",
                                          {"concept": f["external_concept"]},
                                          {"ids": l3vals, "source": "model knowledge, not looked up"}))
        if f.get("cols"):
            do(f"filter-cols-{f['cols']}", "filter_cols", subject=f["cols"])
        if level1:
            do(f"filter-level1-{level1}", "filter_level1", value=level1)
        if level2:
            do("filter-level2-" + " and ".join(level2), "filter_level2", values=level2)
        if l3col and (l3vals or f.get("level3_has_annotation")):
            do(f"filter-level3-{l3col}", "filter_level3", column=l3col, values=l3vals)

        # a pattern / network step without a criterion is a descriptor the LLM put in the wrong slot
        chosen = [st for st in selector.get("steps") or []
                  if st.get("criterion") or st["kind"] not in ("pattern", "ribbon", "network")]
        for st in chosen or [{"kind": "all"}]:
            kind = st["kind"]
            if kind == "pattern" and st.get("criterion") == "compare":
                do("compare patterns and select cluster", "select_by_comparison",
                   tool=st.get("tool") or "opposite", between=st.get("between") or "subjects",
                   a=_slice(st.get("a"), ds), b=_slice(st.get("b"), ds), top_n=st.get("top_n"))
            elif kind == "pattern":
                tp = st.get("timepoint") if st.get("timepoint") in ds.timepoints else None
                do("evaluate pattern and select cluster", "select_by_pattern",
                   criterion=st.get("criterion"), subject=_match(st.get("subject") or "", ds.subjects),
                   timepoint=tp, position=st.get("position"), top_n=st.get("top_n"))
            elif kind == "ribbon":
                do("evaluate ribbon and select cluster", "select_by_ribbon",
                   criterion=st.get("criterion"), measure=st.get("measure"),
                   subject=_match(st.get("subject") or "", ds.subjects), top_n=st.get("top_n"))
            elif kind == "feature_number":
                do("evaluate feature number and select cluster", "select_by_feature_number",
                   top_n=st.get("top_n"))
            elif kind == "network":
                thr = _threshold(st.get("threshold"))
                do("evaluate importance score and select cluster" if thr is not None
                   else "evaluate weight and select cluster",
                   "select_by_network", criterion=st.get("criterion"), threshold=thr)
            elif kind == "feature_lookup":
                do("evaluate features and select cluster", "select_by_feature_lookup", top_n=st.get("top_n"))
            elif kind == "example":
                by = st.get("example_by") or "level2_composition"
                do(f"infer example clusters by {by.replace('_', ' ').replace('level2', 'level-2')}",
                   "select_examples", by=by, top_n=st.get("top_n"))
            elif kind == "given":
                do("select current cluster" if not st.get("clusters") else "select named cluster",
                   "select_given", clusters=st.get("clusters"))
            else:
                do("read cluster data", "select_all")

        table = None
        if l3col and l3vals:
            table = {"action": "table search " + ", ".join(l3vals), "fn": "search table",
                     "param": ",".join(l3vals)}
        elif l3col and f.get("level3_has_annotation"):
            table = {"action": f"click {l3col} (decrease)", "fn": "sort table", "param": f"{l3col} desc"}

        d = descriptor
        counted = any(st["kind"] == "feature_number" for st in chosen)   # counts are already in its result
        if d.get("feature_number") and not counted:
            do("evaluate feature number", "describe_feature_number")
        if d.get("pattern"):
            do("evaluate pattern", "describe_pattern")
        # The class mix is read as the bar shows it. In a level-2 contrast every compared class is
        # counted, although this run keeps one, so the counts of the classes can be set side by side.
        # With one class kept and no contrast the mix is that class alone, a filter artifact: skip it.
        # With several classes kept, always read it, so a message never names a class for a cluster
        # without a finding behind it.
        if contrast_l2:
            do("evaluate level2 (" + " and ".join(f["level2"]) + ")", "describe_level2", classes=f["level2"])
        elif len(level2) > 1 or (d.get("level2") and len(level2) != 1):
            do("evaluate level2", "describe_level2")
        dcol = _match(d.get("level3_column") or "", ds.cfg.level3)
        if dcol:
            res = do("evaluate level3", "describe_level3", column=dcol, mode=d.get("level3_mode") or "frequency")
            top = next((list(v["top"]) for v in res.values() if isinstance(v, dict) and v.get("top")), None)
            if top and not table:
                table = {"action": f"table search {top[0]}", "fn": "search table", "param": top[0]}
        if d.get("weight"):
            do("evaluate weight", "describe_weight", mode=d["weight"])

        runs.append({
            "label": label, "level1": level1, "level2": list(level2),
            "level3": {"column": l3col, "values": l3vals} if l3col else None,
            "threshold": s.threshold,
            "threshold_moved": s.threshold != float(dash_state["min_weight"]),
            "targets": list(s.targets),
            "groups": [{**g, "joined": s.joined(g["clusters"])} for g in s.groups],
            "joined": s.joined(s.targets),
            "table": table, "steps": steps,
            # what the dashboard filter shows: in a contrast every compared value at once, so the
            # bar sets them side by side while each value's clusters are brushed in turn
            "shown_level1": list(f["level1"]) if contrast_l1 else ([level1] if level1 else []),
            "shown_level2": list(f["level2"]) if contrast_l2 else list(level2),
        })
    if len(runs) > 1 and (contrast_l1 or contrast_l2):
        variants = {r["label"]: list(r["targets"]) for r in runs}
        common = set.intersection(*(set(v) for v in variants.values()))
        # how many features of each compared value every picked cluster holds
        col = ds.cfg.level2 if contrast_l2 else ds.cfg.level1
        base = ds.features
        if contrast_l2 and f["level1"] and len(f["level1"]) == 1:
            base = base[base[ds.cfg.level1] == f["level1"][0]]
        picked = sorted(set().union(*variants.values()), key=ds.cluster_number)
        n = base[base["cluster"].isin(picked)].groupby(["cluster", col]).size()
        values = f["level2"] if contrast_l2 else f["level1"]
        counts = {c: {v: int(n.get((c, v), 0)) for v in values} for c in picked}
        result = {"by": f["contrast"], "variants": variants, "counts": counts,
                  "in_all": sorted(common, key=ds.cluster_number),
                  "only": {k: [c for c in v if c not in common] for k, v in variants.items()}}
        runs[-1]["steps"].append(leaves.data_step(
            "compare clusters between " + " and ".join(variants), "compare_variants",
            {"by": f["contrast"]}, result))
    return {"question": question, "filters": f, "selector": selector, "descriptor": descriptor,
            "dropped": dropped, "runs": runs}


def run_data(state: AgentState):
    unit = run_unit(_current(state), state["filters"], state["selector"], state["descriptor"],
                    state["dash_state"])
    log_unit(unit)
    return {"units": state["units"] + [unit], "idx": state["idx"] + 1}


def log_unit(unit):
    """Debug lines for one finished backend pass."""
    for d in unit["dropped"]:
        _debug("data", f"ignored, not in the data: {d}")
    for run in unit["runs"]:
        if run["label"]:
            _debug("data", f"-- filter variant: {run['label']}")
        for st in run["steps"]:
            _debug("data", f"{st['action']}  {_filled(st['args'])}")
            for line in st["findings"]:
                _debug("  finding", line)
        groups = "; ".join((f"{g['label']}: " if g.get("label") else "") + ", ".join(g["clusters"])
                           for g in run["groups"])
        _debug("data", f"target groups: {groups or '(none: answer covers all clusters)'}"
               + (f"   importance score moved to {run['threshold']}" if run["threshold_moved"] else ""))


def route_loop(state: AgentState):
    more = state["idx"] < len(state["sub_questions"])
    return _route("data route", "n3_filters" if more else "n6_display",
                  "next sub-question" if more else "all sub-questions done")


# ---- N6 and leaves ---------------------------------------------------------

def n6_display(state: AgentState):
    units = state["units"]
    picked = [{"question": u["question"], "filter": r["label"], "groups": r["groups"],
               "threshold_moved": r["threshold_moved"]} for u in units for r in u["runs"]]
    user = (f"Question: {state['question']}\n"
            f"Filter slots: {json.dumps([u['filters'] for u in units])}\n"
            f"Selector: {json.dumps([u['selector'] for u in units])}\n"
            f"Descriptor: {json.dumps([u['descriptor'] for u in units])}\n"
            f"Clusters picked by the backend: {json.dumps(picked)}")
    display = _judge(Display, prompts.N6, state, user)
    leaf = leaves.choose_leaf(units, display)
    _debug("N6 display", f"needs_focus={display['needs_focus']}, network_area={display['network_area']}, "
           f"grouping={display['grouping']}: {display['reason']}")
    n_groups = sum(len(r["groups"]) for u in units for r in u["runs"])
    _debug("N6 leaf", f"{leaf}   (computed from the judgement above, {len(units)} sub-question(s), "
           f"{n_groups} target group(s))")
    return {"display": display, "leaf": leaf, "steps": leaves.assemble(leaf, units, display)}


def leaf_L0(state: AgentState):
    _debug("leaf", "L0 out of scope")
    return {"leaf": "L0", "steps": leaves.leaf_L0()}


def leaf_L1(state: AgentState):
    k = state["kind"]
    _debug("leaf", "L1 explain + showcase")
    return {"leaf": "L1", "steps": leaves.leaf_L1(k.get("control"), k.get("value"))}


def leaf_L2(state: AgentState):
    _debug("leaf", "L2 ask")
    return {"leaf": "L2", "steps": leaves.leaf_L2(state["completeness"]["note"])}


def compose_messages(state: AgentState):
    """Write every message text from the data results, then drop the scaffolding."""
    steps = state["steps"]
    slots = [s for s in steps if s["kind"] == "message"]
    # the writer reads the findings only; the full results stay in the steps as evidence
    data = "\n".join(f"[{s['id']}] {s['action']}\n" + "\n".join(f"  - {line}" for line in s["findings"])
                     for s in steps if s["kind"] == "data") or "(no data actions)"
    notes = list(state.get("assumptions") or []) + list((state.get("keyword_map") or {}).get("notes", []))
    for u in state.get("units") or []:
        notes += [f"ignored, not in the data: {d}" for d in u["dropped"]]
    user = (f"QUESTION: {state['question']}\n\n"
            f"ASSUMPTIONS: {json.dumps(notes)}\n\n"
            f"FINDINGS OF THE DATA ACTIONS:\n{data}\n\n"
            "MESSAGE SLOTS:\n" + "\n".join(f"{i + 1}. {json.dumps(s['about'])}  findings: {', '.join(s['evidence']) or 'none'}"
                                         for i, s in enumerate(slots)))
    user += f"\n\nWrite exactly {len(slots)} message(s), one per slot."
    texts = _judge(Messages, prompts.COMPOSE, state, user)["texts"]
    if len(texts) != len(slots):   # the writer sometimes merges slots; ask once more
        _debug("messages", f"got {len(texts)} text(s) for {len(slots)} slot(s), asking again")
        texts = _judge(Messages, prompts.COMPOSE, state, user)["texts"]
    claim = next((m.group(0) for t in texts for m in [ABSENCE.search(t)] if m), None)
    if claim and not _compose_reasoning():
        # the basic writer turns "kept by the filter" into "the cluster has nothing else";
        # the reasoning model reads the counts. Only this case pays for it.
        _debug("messages", f'claims an absence ("{claim}"); rewritten by the reasoning model')
        again = _judge(Messages, prompts.COMPOSE, state, user, force_reasoning=True)["texts"]
        if len(again) == len(slots):
            texts = again
    out, i = [], 0
    for s in steps:
        if s["kind"] == "message":
            s = {"kind": "message", "text": texts[i] if i < len(texts) else "",
                 "evidence": s.get("evidence", [])}
            i += 1
            if not s["text"].strip():   # never play an empty message
                continue
        out.append(s)
    _debug("messages", f"{len(slots)} slot(s), {len(texts)} text(s) written")
    for n, s in enumerate(out, 1):
        if s["kind"] == "dashboard":
            _debug("playback", f"{n:2d}. {s['command']}")
        elif s["kind"] == "message":
            _debug("playback", f"{n:2d}. message: {s['text'][:110]}")
    return {"steps": out}
