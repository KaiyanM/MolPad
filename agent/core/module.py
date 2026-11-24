"""A module: one part of the dashboard, described by a manifest and backed by Python.

    modules/<name>/module.json   the facts
    modules/<name>/ops.py        class Ops: the data operations, as methods of the Session
    modules/<name>/findings.py   RULES = {op: fn(args, result) -> [short text lines]}
    modules/<name>/*.md          skill cards for the plan call

The manifest (every key but name and title is optional):

    name, title
    kind       "view" (a panel of the page) or "shared" (something every view uses)
    js         the page script that draws it (inst/d3dashboard/js/), used by the drift test
    about      one sentence
    method     {"by", "how", "note"}: how the data behind it was made
    shows      {what is drawn: what it stands for}
    reads      {state field: how the part reacts to it}
    writes     {state field: which control of the part sets it}
    features   [{"name", "of", "words", "how", "select", "describe"}]: what can be said about the
               part; "words" are how people ask for it, "select" / "describe" name operations
    ops        names of the data operations (methods of Ops)
    selectors  {selector kind: operation}   how clusters are picked through this part
    criteria   {selector kind: [criterion]} the rules a selector kind offers; a step of such a
               kind needs one
    measures   {measure: operation}         what is reported about the clusters picked
    hints      {"target": {selector kind: words}, "measure": {measure: words},
               "descriptor": {slot: words}}: how a question asks for them; these lines are put
               into the prompts that read the question (parse) and plan the work (plan)
    cards      {name: file}                 skill cards, by the name the planner's roles use
    knowledge  {"file", "writer", "avoid"}  a reference about how the part is made and what its
               results can support (Markdown). "writer" names the heading of the section given
               to the message writer whenever an operation of this part was used; "avoid" lists
               word stems a message resting on this part must not use (checked by code). The
               whole file answers a question about the method itself.
    actions    [{"command", "param", "words"}]: commands the page can play on this part;
               "control" names the control a question about the page can ask for,
               "words_all" is said when the parameter is 'all', "list" marks a parameter
               that is a list of names

ops.py may also define two functions the backend pass calls (agent/nodes.py run_unit):

    select(step, do, ctx)        run the operation(s) for one selector step of a kind in `selectors`
    describe(descriptor, do, ctx) run the operations for the measures in `measures`
    usable(step)                 optional: False for a selector step the module cannot run
    context(ds, dash_state)      optional: lines about the data of this part for the plan call

do(action, op, **args) runs a data operation and records it as a step; ctx holds the session
(ctx.s), the dataset (ctx.ds), the cleaned filters (ctx.f) and what the pass knows so far.
ctx.filtered says whether a filter limits the features; ctx.assume(text) records a reading the
module chose where the question could be read another way: it is shown in the step ("Assumed").

Loading fails when the manifest names an operation, a rule or a card that is not there.
"""

import importlib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

MODULES_DIR = Path(__file__).resolve().parent.parent / "modules"

# The state of the page (inst/d3dashboard/js/state.js): field -> what it holds.
STATE = {
    "level1": "ticked level-1 values (none = All)",
    "level2": "ticked level-2 values (none = All)",
    "scope": "selected clusters show their filtered features, or all of them",
    "selectedClusters": "the clusters picked on the network",
    "minWeight": "importance score: edges above it are drawn",
    "layout": "how the nodes are placed",
    "colourBy": "what the ribbon lines are grouped and coloured by",
    "ribbonExpand": "ribbon plot shows every cluster, or only the selected ones",
}


class ModuleError(ValueError):
    pass


@dataclass(frozen=True)
class Module:
    name: str
    title: str
    kind: str = "view"
    js: str = ""
    about: str = ""
    method: dict = field(default_factory=dict)
    shows: dict = field(default_factory=dict)
    reads: dict = field(default_factory=dict)
    writes: dict = field(default_factory=dict)
    features: tuple = ()
    ops: tuple = ()
    selectors: dict = field(default_factory=dict)
    criteria: dict = field(default_factory=dict)
    measures: dict = field(default_factory=dict)
    hints: dict = field(default_factory=dict)
    cards: dict = field(default_factory=dict)
    knowledge: dict = field(default_factory=dict)
    actions: tuple = ()
    path: Path = None
    Ops: type = None                # the class that holds the operations, when the module has code
    select: object = None           # ops.select, when the module picks clusters
    describe: object = None         # ops.describe, when the module reports on clusters
    usable: object = None           # ops.usable(step): False for a step the module cannot run
    context: object = None          # ops.context(ds, dash_state): lines for the plan call
    rules: dict = field(default_factory=dict)

    def card(self, name):
        return (self.path / self.cards[name]).read_text(encoding="utf-8").strip()

    def reference(self):
        """How this part is made and what it can show: its reference file, else what the
        manifest says (about, method). "" when the module says nothing about it."""
        if self.knowledge.get("file"):
            return (self.path / self.knowledge["file"]).read_text(encoding="utf-8").strip()
        lines = [self.about] if self.method else []
        if self.method:
            lines.append(f"How it is made ({self.method['by']}): {self.method['how']}.")
            if self.method.get("note"):
                lines.append(f"Note: {self.method['note']}.")
        return "\n".join(lines)

    def writer_notes(self):
        """The section of the reference for the message writer (the lines under the heading
        named in knowledge["writer"]); "" when there is none."""
        heading = self.knowledge.get("writer")
        if not heading:
            return ""
        out, inside = [], False
        for line in self.reference().splitlines():
            if line.startswith("#"):
                if inside:
                    break
                inside = heading.lower() in line.lower()
            elif inside:
                out.append(line)
        return "\n".join(out).strip()

    def avoid(self):
        """A pattern for words a message that rests on this part must not use, or None."""
        stems = self.knowledge.get("avoid") or []
        return re.compile(r"(?i)\b(?:" + "|".join(re.escape(s) for s in stems) + r")\w*") if stems else None


def _code(name, part):
    """modules/<name>/<part>.py when the file exists."""
    if not (MODULES_DIR / name / f"{part}.py").exists():
        return None
    return importlib.import_module(f"agent.modules.{name}.{part}")


def load(name, code=True):
    """Read one module. code=False reads the manifest only (no numpy, no data)."""
    path = MODULES_DIR / name
    try:
        m = json.loads((path / "module.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ModuleError(f"module '{name}' has no module.json in {path}") from None
    known = set(Module.__dataclass_fields__) - {"path", "Ops", "rules", "select", "describe", "usable", "context"}
    extra = set(m) - known
    if extra or m.get("name") != name or not m.get("title"):
        raise ModuleError(f"module '{name}': " + (f"unknown keys {sorted(extra)}" if extra else
                                                  "needs 'name' (the folder name) and 'title'"))
    for key in ("reads", "writes"):
        bad = set(m.get(key, {})) - set(STATE)
        if bad:
            raise ModuleError(f"module '{name}' {key} state fields the page does not have: {sorted(bad)}")
    for f in m.get("cards", {}).values():
        if not (path / f).exists():
            raise ModuleError(f"module '{name}' names a card that is not there: {f}")
    know = m.get("knowledge") or {}
    if set(know) - {"file", "writer", "avoid"}:
        raise ModuleError(f"module '{name}' knowledge has unknown keys: {sorted(set(know) - {'file', 'writer', 'avoid'})}")
    if know:
        if not know.get("file") or not (path / know["file"]).exists():
            raise ModuleError(f"module '{name}' names a reference that is not there: {know.get('file')}")
        headings = [l for l in (path / know["file"]).read_text(encoding="utf-8").splitlines() if l.startswith("#")]
        if know.get("writer") and not any(know["writer"].lower() in h.lower() for h in headings):
            raise ModuleError(f"module '{name}': {know['file']} has no heading '{know['writer']}'")
    ops = tuple(m.get("ops", ()))
    named = [f.get(k) for f in m.get("features", ()) for k in ("select", "describe") if f.get(k)]
    named += list(m.get("selectors", {}).values()) + list(m.get("measures", {}).values())
    if set(named) - set(ops):
        raise ModuleError(f"module '{name}' uses operations it does not list in 'ops': "
                          f"{sorted(set(named) - set(ops))}")
    m["features"], m["ops"], m["actions"] = tuple(m.get("features", ())), ops, tuple(m.get("actions", ()))
    Ops, rules, hooks = None, {}, {}
    if code:
        mod = _code(name, "ops")
        Ops = getattr(mod, "Ops", None)
        missing = [o for o in ops if not callable(getattr(Ops, o, None))]
        if missing:
            raise ModuleError(f"module '{name}': ops.py has no Ops.{', Ops.'.join(missing)}")
        rules = dict(getattr(_code(name, "findings"), "RULES", {}))
        if set(ops) - set(rules):
            raise ModuleError(f"module '{name}': findings.py has no rule for {sorted(set(ops) - set(rules))}")
        hooks = {h: getattr(mod, h, None) for h in ("select", "describe", "usable", "context")}
        for h, what in (("select", "selectors"), ("describe", "measures")):
            if m.get(what) and not callable(hooks[h]):
                raise ModuleError(f"module '{name}' has {what} but ops.py has no {h}()")
    return Module(path=path, Ops=Ops, rules=rules, **hooks, **m)


def _names():
    from ..modules import ORDER
    return ORDER


@lru_cache(maxsize=None)
def modules(code=True):
    """Every module, in the order of agent/modules/__init__.py. One operation, selector kind,
    measure, card name and command belongs to one module."""
    out = tuple(load(n, code) for n in _names())
    for what in ("ops", "selectors", "measures", "cards"):
        seen = {}
        for m in out:
            for key in getattr(m, what):
                if key in seen:
                    raise ModuleError(f"{what[:-1]} '{key}' is in two modules: {seen[key]} and {m.name}")
                seen[key] = m.name
    seen = {}
    for m in out:
        for a in m.actions:
            if a["command"] in seen:
                raise ModuleError(f"command '{a['command']}' is in two modules: {seen[a['command']]} and {m.name}")
            seen[a["command"]] = m.name
    return out


def manifests():
    """The modules read from their manifests only: for describing the dashboard."""
    return modules(code=False)


def by_name(name, code=True):
    return next(m for m in modules(code) if m.name == name)


def explainable(code=False):
    """{module name: title} of the parts that can answer a question about how they are made."""
    return {m.name: m.title for m in modules(code) if m.method or m.knowledge}


def writer_notes(ops):
    """[(module, its notes for the writer)] for the modules that own one of the operations."""
    out = []
    for m in modules():
        if set(m.ops) & set(ops) and m.writer_notes():
            out.append((m, m.writer_notes()))
    return out


def owner(what, key, code=True):
    """The module that holds an operation, selector kind, measure or card."""
    return next((m for m in modules(code) if key in getattr(m, what)), None)


def commands(code=False):
    """{command: action} over every module: what the page can be told to do."""
    return {a["command"]: {**a, "module": m.name} for m in modules(code) for a in m.actions}


def named(what, code=False):
    """Every key of one manifest section over the modules, in module order: the selector kinds
    ("selectors"), the measures ("measures") ..."""
    return tuple(k for m in modules(code) for k in getattr(m, what))


def hints(role, code=False):
    """{name: words} of one role ("target", "measure", "descriptor") over the modules."""
    return {k: v for m in modules(code) for k, v in m.hints.get(role, {}).items()}


def controls(code=False):
    """{control: action}: the controls of the page a question can be about."""
    return {a["control"]: a for a in commands(code).values() if a.get("control")}
