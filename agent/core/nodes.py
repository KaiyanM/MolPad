"""What the pipeline in frame.py shares: the state, the backend pass (run_unit), the fixed leaves
and the message writer."""

import contextvars
import json
import os
import re
import sys
import time
from types import SimpleNamespace
from typing import TypedDict

from . import keywords as kw
from . import leaves, prompts
from .module import by_name, modules, writer_notes
from .session import MissingInput
from .session import match as _match
from .data_tools import Session, load_dataset
from ..modules import DESCRIBE_ORDER
from .schemas import Messages

# Set by AGENT_DEBUG=1, `python -m agent.run --debug` or answer(..., debug=True).
DEBUG = os.getenv("AGENT_DEBUG", "").strip() not in ("", "0")

MAX_SUB_CLAIMS = 4

# selector kind -> the module that runs it; the kinds that pick by a criterion; and the modules
# that report on the clusters picked, in the order the answer reports
_OWNER = {kind: m for m in modules() for kind in m.selectors}
NEEDS_CRITERION = {kind for m in modules() for kind in m.criteria}
DESCRIBERS = [by_name(n) for n in DESCRIBE_ORDER]

# Set by answer(): called with one dict per event while the answer is built, so a client can
# show what is known before the whole answer is ready (agent/serve.py). One per run, so answers
# that are built side by side (eval_trace) keep their own.
EMIT = contextvars.ContextVar("agent_emit", default=None)


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


def _emit(event, **fields):
    """Send one event to the client that is waiting for this answer, if there is one."""
    emit = EMIT.get()
    if emit is not None:
        emit({"event": event, **fields})


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


NEGATION = re.compile(r"(?i)\b(?:not|no|never|cannot|can't|without|neither|nor|rather than)\b|n't\b")


def _claimed(pattern, text):
    """The words of `pattern` that `text` uses to claim something. A word in a sentence that
    denies it ("this does not mean that one cluster causes the other") is not a claim."""
    if pattern is None:
        return []
    out = []
    for sentence in re.split(r"(?<=[.!?;])\s+", text):
        if not NEGATION.search(sentence):
            out += pattern.findall(sentence)
    return out


def _compose_reasoning():
    return os.getenv("AGENT_COMPOSE_TIER", "basic").strip().lower() == "reasoning"


def _judge(schema, card, state, user, force_reasoning=False):
    from .llm import ask  # imported late: the rest of the module works without an API key

    # the writer cites the findings only; of the dataset it gets what it is, not its values
    system = card + "\n\nBACKGROUND\n" + prompts.data_block(load_dataset()) + "\n\n" + prompts.views_block()
    # the message writer uses the basic model unless AGENT_COMPOSE_TIER=reasoning
    reasoning = force_reasoning or _compose_reasoning()
    t0 = time.time()
    out = ask(schema, system, user, reasoning=reasoning, site=schema.__name__).model_dump()
    _debug("  llm", f"{schema.__name__} by the {'reasoning' if reasoning else 'basic'} model, "
           f"{time.time() - t0:.1f}s")
    return out


# ---- backend pass ----------------------------------------------------------

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


def run_unit(question, filters, selector, descriptor, dash_state, ds=None):
    """Run the data actions for one (sub-)question. Returns the unit used by the leaf templates."""
    ds = ds or load_dataset()
    f, dropped = clean_filters(filters, ds)
    l3col = f.get("level3_column")
    l3vals = f.get("level3_values") or []
    runs = []
    assumed = []   # inputs a data action needed and the question did not give: the default used
    contrast_l1 = f.get("contrast") == "level1" and len(f["level1"]) > 1
    contrast_l2 = f.get("contrast") == "level2" and len(f["level2"]) > 1

    for label, level1, level2 in _variants(f):
        s = Session(ds, dash_state)
        steps = []

        def do(action, op, **args):
            args = {k: v for k, v in args.items() if v not in (None, [], False)}
            try:
                result = s.run(op, **args)
            except MissingInput as m:      # assume the default and say so in the answer
                args[m.field] = m.default
                note = {"field": m.field, "used": m.default, "options": m.options, "text": m.say}
                if note not in assumed:
                    assumed.append(note)
                result = s.run(op, **args)
            steps.append(leaves.data_step(action, op, args, result))
            return result

        if f.get("external_concept") and l3vals:
            # ids written by the model from memory: every use says so, and says which are in the data
            guessed = f.get("external_ids") or l3vals      # the user may have given ids of their own too
            in_data = kw.ids_in_data(guessed, l3col, ds) if l3col else {}
            steps.append(leaves.data_step(f"llm: search {f['external_concept']}", "llm_search",
                                          {"concept": f["external_concept"]},
                                          {"ids": guessed, "source": "model knowledge, not looked up",
                                           "in_data": in_data}))
            _, text = kw.memory_note(f["external_concept"], guessed, l3col, ds)
            note = {"field": "ids", "used": list(guessed), "options": [], "text": text}
            if note not in assumed:
                assumed.append(note)
        if f.get("cols"):
            do(f"filter-cols-{f['cols']}", "filter_cols", subject=f["cols"])
        if level1:
            do(f"filter-level1-{level1}", "filter_level1", value=level1)
        if level2:
            do("filter-level2-" + " and ".join(level2), "filter_level2", values=level2)
        if l3col and (l3vals or f.get("level3_has_annotation")):
            do(f"filter-level3-{l3col}", "filter_level3", column=l3col, values=l3vals)

        # a step of a kind that picks by a criterion (pattern, network ...) but names none is a
        # descriptor the LLM put in the wrong slot; a module can also refuse a step it cannot run
        chosen = [st for st in selector.get("steps") or []
                  if (st.get("criterion") or st["kind"] not in NEEDS_CRITERION)
                  and (getattr(_OWNER.get(st["kind"]), "usable", None) or (lambda st: True))(st)]
        def assume(text):
            # a module read the question one way where it could be read another: say so in the step
            note = {"field": "clusters", "used": None, "options": [], "text": text}
            if note not in assumed:
                assumed.append(note)

        ctx = SimpleNamespace(s=s, ds=ds, f=f, level2=level2, contrast_l2=contrast_l2, chosen=chosen, table=None,
                              assume=assume,
                              filtered=bool(level1 or level2 or l3vals or f.get("level3_has_annotation")))
        if l3col and l3vals:
            ctx.table = {"action": "table search " + ", ".join(l3vals), "fn": "search table",
                         "param": ",".join(l3vals)}
        elif l3col and f.get("level3_has_annotation"):
            ctx.table = {"action": f"click {l3col} (decrease)", "fn": "sort table", "param": f"{l3col} desc"}
        for st in chosen or [{"kind": "all"}]:
            _OWNER.get(st["kind"], _OWNER["all"]).select(st, do, ctx)
        for m in DESCRIBERS:
            m.describe(descriptor, do, ctx)
        table = ctx.table

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
            "dropped": dropped, "runs": runs, "assumed": assumed}


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


# ---- fixed leaves and the message writer -----------------------------------


def leaf_L0(state: AgentState):
    _debug("leaf", "L0 out of scope")
    return {"leaf": "L0", "steps": leaves.leaf_L0()}


def leaf_L1(state: AgentState):
    k = state["kind"]
    _debug("leaf", "L1 explain + showcase")
    return {"leaf": "L1", "steps": leaves.leaf_L1(k.get("control"), k.get("value"))}


def leaf_method(state: AgentState):
    part = by_name(state["kind"].get("part") or "") or by_name("network")
    _debug("leaf", f"LM explain the method of the {part.title.lower()}")
    return {"leaf": "LM", "steps": leaves.leaf_method(part.title, part.reference())}


def leaf_L2(state: AgentState):
    _debug("leaf", "L2 ask")
    return {"leaf": "L2", "steps": leaves.leaf_L2(state["completeness"]["note"], state["completeness"].get("write"))}


def _slot_texts(out, n):
    """{slot index: text} of a Messages reply; slot numbers outside 1..n and empty texts are ignored."""
    got = {}
    for t in out["texts"]:
        i = t["slot"] - 1
        if 0 <= i < n and t["text"].strip() and i not in got:
            got[i] = t["text"].strip()
    return got


def _fallback_text(slot, by_id):
    """A plain text for a slot the writer left empty twice, so no step of the answer disappears."""
    about = slot["about"]
    if about.get("role") == "conclusion":
        return "No conclusion was written for this answer; the steps above and their evidence stand as they are."
    head = (", ".join(about["clusters"]) + ": " + about["why"]) if about.get("clusters") \
        else (about.get("question") or "")
    last = [by_id[i] for i in slot.get("evidence", []) if i in by_id][-1:]
    return ". ".join(x.rstrip(".") for x in [head] + [l for d in last for l in d["findings"][:2]] if x) + "."


def _findings_text(data_steps):
    return "\n".join(f"[{s['id']}] {s['action']}\n" + "\n".join(f"  - {line}" for line in s["findings"])
                     for s in data_steps) or "(no data actions)"


def _sent(step):
    """A message step as the client gets it: its unit and role stay, the writer's scaffolding goes."""
    out = {"kind": "message", "unit": step.get("unit"), "evidence": step.get("evidence", [])}
    if (step.get("about") or {}).get("role"):
        out["role"] = step["about"]["role"]
    return out


def _slot_groups(slots, n_units):
    """The slots each writer call covers: one call per sub-question, and the conclusion apart.

    Returns (groups, conclusion): groups is [(unit or None, [slot index])]. A single question is
    one group. In an evidence chain every step is written from its own findings only, so the
    calls are small and run side by side; the conclusion is written last, over all of them.
    """
    concl = [i for i, s in enumerate(slots) if s["about"].get("role") == "conclusion"]
    rest = [i for i in range(len(slots)) if i not in concl]
    if n_units <= 1 or any("unit" not in slots[i]["about"] for i in rest):
        return ([(None, rest)] if rest else []), concl
    by_unit = {}
    for i in rest:
        by_unit.setdefault(slots[i]["about"]["unit"], []).append(i)
    return sorted(by_unit.items()), concl


def compose_messages(state: AgentState):
    """Write every message text from the data results, then drop the scaffolding.

    The playback (data steps, dashboard actions, reasoning lines and the empty message slots) is
    sent to the client first; each text follows as soon as it is written.
    """
    from concurrent.futures import ThreadPoolExecutor

    steps = state["steps"]
    slots = [s for s in steps if s["kind"] == "message"]
    n = len(slots)
    by_id = {s["id"]: s for s in steps if s["kind"] == "data" and s.get("id")}
    data_steps = [s for s in steps if s["kind"] == "data"]
    numbered, i = [], 0
    for s in steps:   # what the client plays: a message is a numbered slot without its text yet
        if s["kind"] == "message":
            numbered.append({**_sent(s), "slot": i, "text": None})
            i += 1
        else:
            numbered.append(s)
    _emit("steps", steps=numbered)

    notes = list(state.get("assumptions") or []) + list((state.get("keyword_map") or {}).get("notes", []))
    for u in state.get("units") or []:
        notes += [f"ignored, not in the data: {d}" for d in u["dropped"]]
    groups, concl = _slot_groups(slots, len(state.get("units") or []))
    if concl and _compose_reasoning() and n > 1 and len(groups) == 1:
        groups, concl = [(None, groups[0][1] + concl)], []   # one reasoning call writes everything
    texts = {}

    def slot_lines(wanted):
        return "\n".join(f"{i + 1}. {json.dumps(slots[i]['about'])}  findings: "
                         f"{', '.join(slots[i]['evidence']) or 'none'}" for i in wanted)

    def knowledge(wanted):
        """The notes of the parts whose operations the slots rest on: [(module, notes)]."""
        ops = {by_id[e]["op"] for i in wanted for e in slots[i]["evidence"] if e in by_id}
        return writer_notes(ops)

    def write(user, wanted, force_reasoning=False):
        tail = (f"Write exactly {n} message(s), one per slot." if len(wanted) == n else
                "Write only slot(s) " + ", ".join(str(i + 1) for i in wanted) + ".")
        card = prompts.COMPOSE + "".join(
            f"\n\nWHAT THE {m.title.upper()} CAN SUPPORT (follow this when a message rests on it)\n{notes}"
            for m, notes in knowledge(wanted))
        out = _judge(Messages, card, state, f"{user}\n\n{tail}", force_reasoning=force_reasoning)
        return {i: t for i, t in _slot_texts(out, n).items() if i in wanted}

    def overclaims(got):
        """{slot: words} for texts that use a word the part they rest on cannot support."""
        out = {}
        for i, text in got.items():
            for m, _ in knowledge([i]):
                words = sorted({w.lower() for w in _claimed(m.avoid(), text)})
                if words:
                    out[i] = out.get(i, []) + words
        return out

    def write_group(unit, wanted):
        """The texts of one sub-question (or of the whole single question), sent as they are ready."""
        own = [d for d in data_steps if unit is None or d.get("unit") == unit]
        # what a data action of this step had to assume is said in the step itself
        took = [a["text"] for k, u in enumerate(state.get("units") or []) if unit in (None, k)
                for a in u.get("assumed") or []]
        head = (f"QUESTION: {state['question']}\n\n"
                f"ASSUMPTIONS: {json.dumps((notes if 0 in wanted else []) + took)}\n\n"
                f"FINDINGS OF THE DATA ACTIONS:\n{_findings_text(own)}\n\nMESSAGE SLOTS:\n")
        got = write(head + slot_lines(wanted), wanted)
        missing = [i for i in wanted if i not in got]
        if missing:   # the writer sometimes merges slots; ask once more for the ones it left out
            _debug("messages", f"got {len(got)} text(s) for {len(wanted)} slot(s), asking again for "
                   + ", ".join(str(i + 1) for i in missing))
            got.update(write(head + slot_lines(missing), missing))
        # The basic writer turns "kept by the filter" into "the cluster has nothing else"; the
        # reasoning model reads the counts. Only the slots that make such a claim are rewritten.
        absent = [] if _compose_reasoning() else [i for i in got if ABSENCE.search(got[i])]
        if absent:
            _debug("messages", "slot(s) " + ", ".join(str(i + 1) for i in absent)
                   + " claim an absence; rewritten by the reasoning model")
            got.update(write(head + slot_lines(absent), absent, force_reasoning=True))
        strong = overclaims(got)
        if strong:
            # "X drives Y", "a significant link": the network shows prediction, not cause or a test
            _debug("messages", "; ".join(f"slot {i + 1} says {', '.join(w)}" for i, w in strong.items())
                   + ": written once more without these words")
            again = head + slot_lines(list(strong)) + "\n\nREWRITE: " + " ".join(
                f"Slot {i + 1} used {', '.join(repr(x) for x in w)}, which the findings cannot support; "
                "say the same without claiming a cause, a direction or a test." for i, w in strong.items())
            got.update(write(again, list(strong)))
        for i in wanted:
            if i not in got:   # never drop a step of the answer silently
                _debug("messages", f"slot {i + 1} was left empty twice; filled from its findings")
                got[i] = _fallback_text(slots[i], by_id)
            _emit("text", slot=i, text=got[i])
        return got

    if len(groups) > 1:
        # one writer per step, side by side; each thread keeps this run's usage log
        with ThreadPoolExecutor(max_workers=len(groups)) as pool:
            jobs = [pool.submit(contextvars.copy_context().run, write_group, u, w) for u, w in groups]
            for job in jobs:
                texts.update(job.result())
    else:
        for u, w in groups:
            texts.update(write_group(u, w))

    if concl:
        # The conclusion of an evidence chain is an argument over all the steps: the reasoning
        # model writes it from every finding and the step messages. One extra call per hypothesis.
        written = "\n".join(f"{i + 1}. {texts[i]}" for i in sorted(texts))
        user = (f"QUESTION: {state['question']}\n\nASSUMPTIONS: []\n\n"
                f"FINDINGS OF THE DATA ACTIONS:\n{_findings_text(data_steps)}\n\n"
                f"MESSAGE SLOTS:\n{slot_lines(concl)}\n\n"
                "MESSAGES ALREADY WRITTEN FOR THE OTHER SLOTS (the assumptions are stated there; "
                f"do not repeat them):\n{written}")
        got = write(user, concl, force_reasoning=True)
        for i in concl:
            if i not in got:
                _debug("messages", f"slot {i + 1} was left empty; filled with the fallback")
                got[i] = _fallback_text(slots[i], by_id)
            _emit("text", slot=i, text=got[i])
        texts.update(got)

    out, i = [], 0
    for s in steps:
        if s["kind"] == "message":
            s = {**_sent(s), "text": texts[i]}
            i += 1
        out.append(s)
    _debug("messages", f"{len(slots)} slot(s), {len(texts)} text(s) written")
    for k, s in enumerate(out, 1):
        if s["kind"] == "dashboard":
            _debug("playback", f"{k:2d}. {s['command']}")
        elif s["kind"] in ("message", "reasoning"):
            _debug("playback", f"{k:2d}. {s['kind']}: {s['text'][:110]}")
        elif s["kind"] == "unit":
            _debug("playback", f"{k:2d}. unit {s['unit'] + 1} of {s['of']}: {s['question']}")
            for line in s["assumed"] + [s["overview"]]:
                _debug("playback", f"      {line[:140]}")
    return {"steps": out}
