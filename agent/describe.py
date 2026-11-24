"""Describe the dashboard from its modules: what each part shows, its features, and the links.

    python -m agent.describe            for a person (Markdown)
    python -m agent.describe --json     the same facts as JSON
    python -m agent.describe ribbon     one module
    python -m agent.describe --dashboard index.html [--context my.json]
                                        starts with what that page's dataset is, and uses its words
"""

import argparse
import json

from .core import prompts
from .core import datacard, links
from .core.module import STATE, commands, manifests


def _rows(d):
    return [f"- {k}: {v}" for k, v in d.items()]


def module_text(m):
    out = [f"## {m.title}", "", m.about]
    if m.method:
        out += ["", f"How it is made ({m.method['by']}): {m.method['how']}."]
        if m.method.get("note"):
            out += [f"Note: {m.method['note']}."]
    if m.shows:
        out += ["", "Shows"] + _rows(m.shows)
    if m.reads:
        out += ["", "Follows"] + _rows(m.reads)
    if m.writes:
        out += ["", "Sets"] + _rows(m.writes)
    if m.features:
        out += ["", "Features"]
        for f in m.features:
            ops = ", ".join(f"{k} with {f[k]}" for k in ("select", "describe") if f.get(k))
            out += [f"- {f['name']} (per {f['of']}): {f['how']}.",
                    f"  People say: {', '.join(f['words'])}." + (f" Agent: {ops}." if ops else "")]
    if m.actions:
        out += ["", "Commands"] + [f"- {a['command']}" + (f": {a['param']}" if a["param"] else "")
                                   for a in m.actions]
    return "\n".join(out)


def links_text(mods=None):
    mods = mods or manifests()
    title = {m.name: m.title for m in mods}
    out = ["## How the parts are linked", "",
           "The page keeps one shared state. A part is linked to another when it follows a field "
           "the other sets.", ""]
    for row in links.table(mods):
        out.append(f"{row['field']}: {row['meaning']}")
        out += [f"- set by the {title[n].lower()}: {how}" for n, how in row["set_by"].items()]
        out += [f"- {title[n]}: {how}" for n, how in row["read_by"].items()]
        out.append("")
    return "\n".join(out).rstrip()


def dataset_text(ds):
    """What the dataset of a page is: its card (core/datacard.py), one fact per line."""
    return "\n".join(["## The dataset", ""] + [f"- {line}" for line in datacard.lines(ds.card, ds)])


def text(names=None, ds=None):
    mods = [m for m in manifests() if not names or m.name in names]
    parts = [] if names else ["# The dashboard, part by part"]
    if ds is not None and not names:
        parts.append(dataset_text(ds))
    parts += [module_text(m) for m in mods]
    if not names:
        parts.append(links_text())
    return prompts.for_data("\n\n".join(parts), ds)


def as_json(names=None, ds=None):
    mods = [m for m in manifests() if not names or m.name in names]
    keys = ("name", "title", "kind", "about", "method", "shows", "reads", "writes", "features", "actions")
    out = {"state": STATE, "modules": [{k: getattr(m, k) for k in keys} for m in mods],
           "links": links.table(), "commands": sorted(commands())}
    out = json.loads(prompts.for_data(json.dumps(out), ds))
    return {"dataset": ds.card, **out} if ds is not None else out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("modules", nargs="*", help="module names; default: all")
    p.add_argument("--json", action="store_true")
    p.add_argument("--dashboard", help="index.html written by gDashboard_d3(): describe its dataset too")
    p.add_argument("--context", help="JSON file that overrules the page's dataset description")
    a = p.parse_args()
    ds = None
    if a.dashboard:
        from .core.payload import load
        ds = load(a.dashboard, a.context)
    known = [m.name for m in manifests()]
    bad = [n for n in a.modules if n not in known]
    if bad:
        p.error(f"unknown module {', '.join(bad)}; choose from {', '.join(known)}")
    print(json.dumps(as_json(a.modules, ds), indent=2) if a.json else text(a.modules, ds))


if __name__ == "__main__":
    main()
