"""Leaf templates L0-L8: slots and data results -> ordered steps.

Pure Python, no LLM. A step is one of

    {"kind": "data",      "id", "action", "op", "args", "findings", "result"}
    {"kind": "dashboard", "action", "command", "supported"}
    {"kind": "message",   "text", "about", "evidence"}
    {"kind": "unit",      "unit", "of", "question", "reason", "assumed", "overview"}
    {"kind": "reasoning", "text", "unit"}

The answer is a list of units, one per (sub-)question. A unit step opens each one: it
carries the sub-question, why it is asked, what had to be assumed, and an overview that
names the dashboard actions of the unit in the order they are played. Every dashboard
and message step that follows carries the same `unit` number, so the chat can show the
logic first and the actions under it. The texts of a unit step are fixed here, not
written by the message writer, so they cannot get lost.

Data steps come first because they decide what is shown. Dashboard steps and
messages then follow in playback order. Message texts are left empty here and
written afterwards from `about` and the findings of the data steps.

A data step keeps its findings (short lines, see findings.py) apart from its
result (the full numbers). A message lists in `evidence` the ids of the data
steps it rests on, so the dashboard can show their numbers under it.
"""

from .config import SUPPORTED_COMMANDS
from .findings import conclude


def data_step(action, op, args, result):
    return {"kind": "data", "action": action, "op": op, "args": args,
            "findings": conclude(op, args, result), "result": result}


def dash_step(action, fn, param=None):
    command = fn if param is None else f"{fn}:{param}"
    return {"kind": "dashboard", "action": action, "command": command,
            "supported": fn in SUPPORTED_COMMANDS}


def message_step(about, text=""):
    return {"kind": "message", "text": text, "about": about, "evidence": []}


def reasoning_step(text, unit=None):
    return {"kind": "reasoning", "text": text, "unit": unit}


def unit_step(unit, of, question, reason="", assumed=()):
    return {"kind": "unit", "unit": unit, "of": of, "question": question, "reason": reason or "",
            "assumed": list(assumed), "overview": ""}


def _overview(steps):
    """One sentence that names the dashboard actions of a unit in the order they are played."""
    parts = []
    for s in steps:
        if s["kind"] != "dashboard":
            continue
        fn, _, param = s["command"].partition(":")
        if fn in ("set filter1", "set filter2"):
            parts.append(f"clear filter {fn[-1]}" if param == "all" else f"set filter {fn[-1]} to {param}")
        elif fn == "set importance":
            parts.append(f"move the importance score to {param}")
        elif fn == "search table":
            parts.append(f"search the table for {param}")
        elif fn == "sort table":
            parts.append(f"sort the table by {param}")
        elif fn in ("brush node", "select node"):
            parts.append(f"{fn.split()[0]} {', '.join(param.split(','))}"
                         + (f" ({s['why']})" if s.get("why") else ""))
        else:
            parts.append(s["command"])
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][0].upper() + parts[0][1:] + "."
    return "First " + parts[0] + "".join(f", then {p}" for p in parts[1:]) + "."


def attach_evidence(steps):
    """Give each message the ids of the data steps it rests on.

    A message about one (sub-)question run gets the data steps of that run; a message
    without one (the conclusion of an evidence chain) gets all of them.
    """
    data = [s for s in steps if s["kind"] == "data" and s.get("id")]
    for s in steps:
        if s["kind"] != "message":
            continue
        about = s.get("about") or {}
        if "unit" in about:
            s["evidence"] = [d["id"] for d in data
                             if d.get("unit") == about["unit"] and d.get("run") == about.get("run")]
        else:
            s["evidence"] = [d["id"] for d in data]
    return steps


class _Playback:
    """Collects dashboard steps and remembers what this sequence has already set."""

    def __init__(self):
        self.steps = []
        self.level1 = None
        self.level2 = []
        self.threshold = None
        self.table_set = None
        self.focus = None     # the clusters in focus now
        self.seen = set()     # clusters an earlier message has already covered
        self.unit = None      # the unit the next steps belong to

    def _add(self, step):
        step["unit"] = self.unit
        self.steps.append(step)
        return step

    def filters(self, run):
        """Set the shared filters to what the run shows; a contrast shows all its values at once.

        A filter 1 that an earlier unit set is cleared when this run reads every level-1 value,
        so the dashboard shows the data the run was computed on.
        """
        level1 = run.get("shown_level1", [run["level1"]] if run.get("level1") else [])
        if level1 != (self.level1 or []):
            self.level1 = list(level1)
            self._add(dash_step("click level1 drop-down-" + (" and ".join(level1) or "all"),
                                "set filter1", ", ".join(level1) or "all"))
        level2 = run.get("shown_level2", run.get("level2") or [])
        if level2 != self.level2:
            self.level2 = list(level2)
            self._add(dash_step("click level2 drop-down-" + (" and ".join(level2) or "all"),
                                "set filter2", ", ".join(level2) or "all"))

    def slider(self, run):
        if run.get("threshold_moved") and run["threshold"] != self.threshold:
            self.threshold = run["threshold"]
            self.focus = None   # the network is redrawn, so the next group is brushed again
            self._add(dash_step("drag importance score", "set importance", self.threshold))

    def table(self, run):
        t = run.get("table")
        if t and (t["fn"], t["param"]) != self.table_set:   # the table keeps its search between steps
            self.table_set = (t["fn"], t["param"])
            self._add(dash_step(t["action"], t["fn"], t["param"]))

    def show(self, clusters, joined=False, brush=False, why=None):
        """Put the clusters in focus: one rectangle when they sit together, else clicks.

        "brush node" draws one rectangle when one exists that holds only these
        nodes (the dashboard falls back to clicks when none does). "select node"
        is clear all, then a click on each node in turn.

        Clusters that are in focus already are not brushed a second time. Returns True
        when an earlier message has covered every one of them. `why` is the short reason
        the unit's overview gives for this action.
        """
        seen_before = set(clusters) <= self.seen
        self.seen |= set(clusters)
        if list(clusters) == self.focus:
            return seen_before
        self.focus = list(clusters)
        if len(clusters) == 1 or joined or brush:
            action = "brush selected cluster" + ("s" if len(clusters) > 1 else "")
            step = dash_step(action, "brush node", ",".join(clusters))
        else:
            step = dash_step("click clear all; click selected clusters", "select node", ",".join(clusters))
        if why:
            step["why"] = why
        self._add(step)
        return seen_before

    def say(self, **about):
        self._add(message_step(about))


WHY_FIRST = ("first sentence: why these clusters are in focus, from `why` and the class mix in the "
             "findings; then what they show for the question")


def _why(run, group):
    """Why a group is shown: the example finder's reason, else the selector's label and rule."""
    if group.get("why"):
        return group["why"]
    rule = next((st["findings"][0] for st in run.get("steps", []) if st["op"].startswith("select_")
                 and st["findings"] and st["findings"][0].startswith(("metric:", "rule:"))), None)
    label = group.get("label")
    return "; ".join(x for x in (f"picked as {label}" if label else "picked by the selector", rule) if x)


def _brief(run, group, limit=90):
    """A few words on why a group is shown, for the overview of its unit."""
    text = group.get("label")
    if not text:
        rule = next((st["findings"][0] for st in run.get("steps", []) if st["op"].startswith("select_")
                     and st["findings"] and st["findings"][0].startswith(("metric:", "rule:"))), "")
        text = rule.split(":", 1)[1].strip() if rule else ""
    return text if len(text) <= limit else text[:limit - 3].rsplit(" ", 1)[0] + "..."


SEEN_BEFORE = ("an earlier message already introduced these clusters: do not repeat why they were "
               "picked or what was said; say only what this step adds")


def _focus(run, group, seen_before=False):
    """The message-slot fields of a group in focus."""
    about = {"group": group.get("label"), "clusters": group["clusters"], "why": _why(run, group),
             "write": SEEN_BEFORE if seen_before else WHY_FIRST}
    if seen_before:
        about["seen_before"] = True
    return about


def _groups(run, one_by_one=False):
    """Groups of a run, as the playback puts them in focus.

    Clusters picked by one rule for one reason stay one group and are shown together.
    A group is split into single clusters when the clusters were found through the graph
    structure (neighbours, connectivity, most edges), or when each cluster is its own
    answer (`one_by_one`, for a run with a single group).
    """
    groups = run.get("groups") or []
    each = one_by_one and len(groups) == 1
    out = []
    for g in groups:
        if len(g["clusters"]) > 1 and (each or g.get("via") == "network"):
            out += [{**g, "clusters": [c], "joined": False} for c in g["clusters"]]
        else:
            out.append(g)
    return out


def _same_view(runs):
    """True when every run of a unit is shown under the same filters and table (a contrast)."""
    def view(r):
        return (r.get("shown_level1", [r.get("level1")]), r.get("shown_level2", r.get("level2")),
                r.get("table"), r.get("threshold") if r.get("threshold_moved") else None)
    return all(view(r) == view(runs[0]) for r in runs)


def _focus_order(runs, one_by_one):
    """(run index, group) pairs in the order they are put in focus.

    Run by run. When the runs share one view of the dashboard (the sides of a contrast), a group
    that several runs picked is shown once and each run says its part, instead of the same
    clusters being brushed again for every side.
    """
    pairs = [(ri, g) for ri, run in enumerate(runs) for g in _groups(run, one_by_one)]
    if len(runs) > 1 and _same_view(runs):
        first = {}
        for n, (_, g) in enumerate(pairs):
            first.setdefault(tuple(g["clusters"]), n)
        pairs.sort(key=lambda p: first[tuple(p[1]["clusters"])])   # stable: runs keep their order
    return pairs


def choose_leaf(units, display):
    """N6, the computed part: pick L3-L8 from the display judgement and the data results."""
    if len(units) > 1:
        return "L7"
    runs = units[0]["runs"]
    filtered = any(r.get("level1") or r.get("level2") or r.get("level3") or r.get("threshold_moved")
                   for r in runs)
    groups = [g for r in runs for g in _groups(r, display["grouping"] == "one_by_one")]
    if not display["needs_focus"] or not groups:
        return "L4" if filtered else "L3"
    if display["network_area"] or any(r.get("threshold_moved") for r in runs):
        return "L8"
    if len(groups) == 1 and len(groups[0]["clusters"]) == 1:
        return "L5"
    if len(groups) > 1:
        return "L7"
    return "L6"


def leaf_L0():
    """Out of scope."""
    return [message_step({"leaf": "L0", "write": "say this needs a manual gesture or depends on the "
                          "screen layout, and offer a data version of the question"})]


def leaf_L1(control, value):
    """Explain + showcase."""
    fn = {"layout": "set layout", "importance": "set importance", "level1": "set filter1",
          "level2": "set filter2", "table": "search table"}.get(control or "layout", "set layout")
    steps = []
    if value:
        steps.append(dash_step(f"switch {control or 'layout'}", fn, value))
    steps.append(message_step({"leaf": "L1", "write": "explain what the control is for and whether it helps here"}))
    return steps


def leaf_L2(note):
    """Ask."""
    return [message_step({"leaf": "L2", "write": "ask for a specific cluster, or an overview", "missing": note})]


CONCLUDE = {
    "evidence_chain": "conclusion: answer the original question, argued yes/no over the steps above: "
                      "say which step supports it and which weakens it, and do not claim more than "
                      "the findings show; say that the dashboard gives evidence and does not prove cause",
    "multi_step": "conclusion: answer the original question in one to three sentences from the steps "
                  "above, naming the clusters and the measure each step found; state what a step "
                  "assumed (`assumed`), and do not claim more than the findings show",
}


def assemble(leaf, units, display, shape="evidence_chain"):
    """Steps for L3-L8. `units` is one entry per (sub-)question, each with its runs.

    `shape` is the reasoning shape of the question: it decides how the conclusion over
    several units is written (an argument for a hypothesis, a plain answer for a question
    that only needed several steps).
    """
    steps = [{**s, "id": None, "unit": ui, "run": ri}
             for ui, u in enumerate(units) for ri, r in enumerate(u["runs"]) for s in r["steps"]]
    for i, s in enumerate(steps, 1):
        s["id"] = f"d{i}"
    play = _Playback()
    # In an evidence chain the origin of a group decides how it is shown (see _groups); the
    # display judgement "one_by_one" splits a group only for a single question.
    one_by_one = len(units) == 1 and display["grouping"] == "one_by_one"
    shown = 0   # groups put in focus one after another

    for ui, unit in enumerate(units):
        play.unit = ui
        if len(units) > 1:
            why = (unit.get("reason") or "").strip()
        else:
            why = (display.get("reason") or "") if leaf in ("L5", "L6", "L7", "L8") else ""
        head = play._add(unit_step(ui, len(units), unit["question"], why,
                                   [a["text"] for a in unit.get("assumed") or []]))
        start = len(play.steps)
        wheres = []   # L7: the message fields of each run, filled before its groups are shown
        for ri, run in enumerate(unit["runs"]):
            d = unit.get("descriptor") or {}
            report = [k for k in ("pattern", "level2", "weight", "feature_number") if d.get(k)]
            report += [f"level3 {d['level3_column']}"] if d.get("level3_column") else []
            where = {"leaf": leaf, "unit": ui, "run": ri, "question": unit["question"],
                     "filter": run.get("label"), "report": report}
            if len(units) > 1 and unit.get("reason"):
                where["purpose"] = unit["reason"]
            if leaf == "L3":
                play.say(**where)
            elif leaf == "L4":
                play.filters(run)
                play.slider(run)
                play.table(run)
                play.say(**where)
            elif leaf in ("L5", "L6"):
                one = run["groups"][0] if len(run["groups"]) == 1 else {}
                group = {"clusters": run["targets"], "joined": run.get("joined", False),
                         "label": one.get("label"), "why": one.get("why")}
                play.filters(run)
                play.show(group["clusters"], group["joined"], why=_brief(run, group))
                play.table(run)
                play.say(**where, **_focus(run, group))
            elif leaf == "L7":
                if not _groups(run, one_by_one):
                    play.filters(run)
                    play.table(run)
                    play.say(**where)
                wheres.append(where)
                if ri < len(unit["runs"]) - 1:
                    continue
                pairs = _focus_order(unit["runs"], one_by_one)
                for rj, g in pairs:
                    other = unit["runs"][rj]
                    play.filters(other)
                    seen = play.show(g["clusters"], g.get("joined", False), why=_brief(other, g))
                    play.table(other)
                    play.say(**wheres[rj], **_focus(other, g, seen))
                shown += len(pairs)
            elif leaf == "L8":
                play.filters(run)
                play.slider(run)
                groups = _groups(run, one_by_one)
                for g in groups:
                    seen = play.show(g["clusters"], brush=True, why=_brief(run, g))
                    play.say(**where, **_focus(run, g, seen))
                shown += len(groups)
            else:
                raise ValueError(f"unknown leaf {leaf}")
        head["overview"] = _overview(play.steps[start:])

    if len(units) > 1:
        play.unit = None    # the conclusion stands after the units, not inside the last one
        assumed = [a["text"] for u in units for a in u.get("assumed") or []]
        play.say(leaf=leaf, role="conclusion", steps=[u["question"] for u in units],
                 write=CONCLUDE.get(shape, CONCLUDE["evidence_chain"]),
                 **({"assumed": assumed} if assumed else {}))
    elif shown > 1:
        play.say(leaf=leaf, question=units[0]["question"],
                 write="compare the groups shown above and answer the question in one or two sentences. "
                       "Compare per sample group: in each group, set the clusters' peaks (or flat "
                       "shapes) side by side; never compare a timepoint of one sample group with "
                       "a timepoint of another")
    return attach_evidence(steps + play.steps)
