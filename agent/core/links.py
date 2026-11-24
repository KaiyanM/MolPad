"""How the parts of the dashboard are linked, read from the modules' manifests.

The page has one shared state (core/module.STATE). A part is linked to another when it reads a
field the other writes: brushing the network writes selectedClusters, and the bar, the ribbon
plot and the table read it.
"""

from .module import STATE, manifests


def table(mods=None):
    """[{"field", "meaning", "set_by": {module: how}, "read_by": {module: how}}], one per state field."""
    mods = mods or manifests()
    return [{"field": f, "meaning": STATE[f],
             "set_by": {m.name: m.writes[f] for m in mods if f in m.writes},
             "read_by": {m.name: m.reads[f] for m in mods if f in m.reads}} for f in STATE]


def links(mods=None):
    """[(from module, state field, to module)]: a control of `from` changes what `to` shows."""
    return [(a, row["field"], b) for row in table(mods) for a in row["set_by"]
            for b in row["read_by"] if a != b]


def follows(name, mods=None):
    """{state field: how} for one module, with who sets the field."""
    out = {}
    for row in table(mods):
        if name in row["read_by"]:
            out[row["field"]] = {"how": row["read_by"][name], "set_by": sorted(row["set_by"])}
    return out
