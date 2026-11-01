"""Leaf templates L0-L8: slots and data results -> ordered steps.

Pure Python, no LLM. A step is one of

    {"kind": "data",      "id", "action", "op", "args", "findings", "result"}
    {"kind": "dashboard", "action", "command", "supported"}
    {"kind": "message",   "text", "about", "evidence"}

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

    def filters(self, run):
        if run.get("level1") and run["level1"] != self.level1:
            self.level1 = run["level1"]
            self.steps.append(dash_step(f"click level1 drop-down-{self.level1}", "set filter1", self.level1))
        level2 = run.get("level2") or []
        if level2 != self.level2:
            self.level2 = list(level2)
            self.steps.append(dash_step("click level2 drop-down-" + (" and ".join(level2) or "all"),
                                        "set filter2", ",".join(level2) or "all"))

    def slider(self, run):
        if run.get("threshold_moved") and run["threshold"] != self.threshold:
            self.threshold = run["threshold"]
            self.steps.append(dash_step("drag importance score", "set importance", self.threshold))

    def table(self, run):
        t = run.get("table")
        if t and (t["fn"], t["param"]) != self.table_set:   # the table keeps its search between steps
            self.table_set = (t["fn"], t["param"])
            self.steps.append(dash_step(t["action"], t["fn"], t["param"]))

    def show(self, clusters, joined=False, brush=False):
        """Put the clusters in focus: one rectangle when they sit together, else clicks.

        "brush node" draws one rectangle when one exists that holds only these
        nodes (the dashboard falls back to clicks when none does). "select node"
        is clear all, then a click on each node in turn.
        """
        if len(clusters) == 1 or joined or brush:
            action = "brush selected cluster" + ("s" if len(clusters) > 1 else "")
            self.steps.append(dash_step(action, "brush node", ",".join(clusters)))
        else:
            self.steps.append(dash_step("click clear all; click selected clusters", "select node",
                                        ",".join(clusters)))

    def say(self, **about):
        self.steps.append(message_step(about))


def _groups(run, one_by_one=False):
    """Groups of a run; split into single clusters when each is its own answer."""
    groups = run.get("groups") or []
    if one_by_one and len(groups) == 1 and len(groups[0]["clusters"]) > 1:
        return [{"label": groups[0].get("label"), "clusters": [c], "joined": False}
                for c in groups[0]["clusters"]]
    return groups


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


def assemble(leaf, units, display):
    """Steps for L3-L8. `units` is one entry per (sub-)question, each with its runs."""
    steps = [{**s, "id": None, "unit": ui, "run": ri}
             for ui, u in enumerate(units) for ri, r in enumerate(u["runs"]) for s in r["steps"]]
    for i, s in enumerate(steps, 1):
        s["id"] = f"d{i}"
    play = _Playback()
    one_by_one = leaf == "L7" or display["grouping"] == "one_by_one"

    for ui, unit in enumerate(units):
        for ri, run in enumerate(unit["runs"]):
            d = unit.get("descriptor") or {}
            report = [k for k in ("pattern", "level2", "weight", "feature_number") if d.get(k)]
            report += [f"level3 {d['level3_column']}"] if d.get("level3_column") else []
            where = {"leaf": leaf, "unit": ui, "run": ri, "question": unit["question"],
                     "filter": run.get("label"), "report": report}
            if leaf == "L3":
                play.say(**where)
            elif leaf == "L4":
                play.filters(run)
                play.slider(run)
                play.table(run)
                play.say(**where)
            elif leaf in ("L5", "L6"):
                group = {"clusters": run["targets"], "joined": run.get("joined", False)}
                play.filters(run)
                play.show(group["clusters"], group["joined"])
                play.table(run)
                play.say(**where, clusters=group["clusters"])
            elif leaf == "L7":
                groups = _groups(run, one_by_one)
                if not groups:
                    play.filters(run)
                    play.table(run)
                    play.say(**where)
                for g in groups:
                    play.filters(run)
                    play.show(g["clusters"], g.get("joined", False))
                    play.table(run)
                    play.say(**where, group=g.get("label"), clusters=g["clusters"])
            elif leaf == "L8":
                play.filters(run)
                play.slider(run)
                for g in _groups(run, display["grouping"] == "one_by_one"):
                    play.show(g["clusters"], brush=True)
                    play.say(**where, group=g.get("label"), clusters=g["clusters"])
            else:
                raise ValueError(f"unknown leaf {leaf}")

    if len(units) > 1:
        play.say(leaf=leaf, write="conclusion: argued yes/no over the steps above; say that the "
                 "dashboard gives evidence and does not prove cause")
    return attach_evidence(steps + play.steps)
