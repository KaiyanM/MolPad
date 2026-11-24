"""What the data operations of the network found, as short text lines (agent/findings.py)."""

from ...core.text import _f, _groups, _list, _order


def _select_by_network(args, r):
    lines = [f"importance score {_f(r['threshold'])}"]
    if "n_components" in r:
        return lines + [_components(r)]
    if r.get("edge"):
        e = r["edge"]
        return lines + [f"strongest edge {e['from']} - {e['to']}, weight {_f(e['weight'])}"]
    if r.get("edges_per_cluster") and args.get("criterion") == "most_edges":
        top = max(r["edges_per_cluster"].values())
        return lines + [f"most edges ({top}): {_list(g['clusters'])}" for g in r["groups"]]
    if "within" in r:       # connectivity: are the clusters picked before linked to one another?
        base = list(r.get("neighbours") or {})
        if len(base) > 1:
            lines.append((f"links among {_list(base)}: " + ", ".join(
                f"{e['from']} - {e['to']} (weight {_f(e['weight'])})" for e in r["within"]))
                if r["within"] else f"no link among {_list(base)} at this score")
        for cl in base:
            nb = r["neighbours"][cl]
            lines.append(f"{cl}: " + ("linked to " + ", ".join(_order(nb)) if nb else "isolated"))
        return lines
    return lines + _groups(r)


def _components(r):
    sizes = sorted((len(c) for c in r.get("components", [])), reverse=True)
    return f"{r['n_components']} connected components" + (f" (sizes {', '.join(map(str, sizes))})" if sizes else "")


def _describe_weight(args, r):
    lines = [f"importance score {_f(r['threshold'])}"]
    if "n_components" in r:
        return lines + [_components(r)]
    if "edges_per_cluster" in r:
        e = r["edges_per_cluster"]
        return lines + ["edges: " + ", ".join(f"{c} {e[c]}" for c in _order(e))]
    for cl in _order(r["neighbours"]):
        nb = r["neighbours"][cl]
        lines.append(f"{cl}: " + (", ".join(_order(nb)) if nb else "no neighbours"))
    return lines


RULES = {
    "select_by_network": _select_by_network,
    "describe_weight": _describe_weight,
}
