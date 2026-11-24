"""What the data operations of the stacked bar plot found, as short text lines (agent/findings.py)."""

from ...core.text import _f, _list, _order


def _select_examples(args, r):
    lines = [f"{g['label']}: {_list(g['clusters'])} ({g['why']})" for g in r.get("groups") or []]
    return lines or [f"no example cluster for {', '.join(r.get('values') or [])}"]


def _describe_level2(args, r):
    """Counts, as the stacked bar shows them; a share only of the whole cluster."""
    lines = []
    for cl in _order(r):
        v = r[cl]
        counts = sorted(v["counts"].items(), key=lambda kv: -kv[1])
        if v.get("classes"):
            scope = f"counting {' and '.join(v['classes'])}"
        elif v.get("kept"):
            scope = f"of the features kept by the level-2 filter ({', '.join(v['kept'])})"
        else:
            scope = "of the features kept by the filters"
        shown = counts if v.get("classes") else counts[:3]
        lines.append(f"{cl}: " + ", ".join(f"{k} {_f(n)}" for k, n in shown)
                     + f" ({scope}; the cluster has {_f(v.get('cluster_total'))} features in all)")
    return lines


RULES = {
    "select_examples": _select_examples,
    "describe_level2": _describe_level2,
}
