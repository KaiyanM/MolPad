"""What the data operations of the feature table (level 3) found, as short text lines (agent/findings.py)."""

from ...core.text import _f, _order, _pct


def _filter_level3(args, r):
    lines = [f"kept {_f(r['n_features'])} features by {args.get('column')}"
             + (f" ({r['kept']})" if r.get("kept") else "")]
    per = r.get("features_per_id") or {}
    missing = [i for i, n in per.items() if not n]
    if per:
        lines.append("features per id: " + ", ".join(f"{i} {n}" for i, n in per.items() if n)
                     + (f"; not found: {', '.join(missing)}" if missing else ""))
    return lines


def _llm_search(args, r):
    lines = [f"ids for {args.get('concept')} from model knowledge, not looked up: "
             + ", ".join(r.get("ids", []))]
    found = r.get("in_data") or {}
    if found:
        absent = [i for i, n in found.items() if not n]
        lines.append("in the data: " + (", ".join(f"{i} ({n} features)" for i, n in found.items() if n) or "none")
                     + (f"; not in the data: {', '.join(absent)}" if absent else ""))
    return lines


def _select_by_feature_lookup(args, r):
    per = r.get("features_per_cluster") or {}
    if not per:
        return ["no feature matches"]
    return [f"{_f(r['n_features'])} matching features in "
            + ", ".join(f"{c} ({per[c]})" for c in _order(per))]


def _describe_level3(args, r):
    col, mode = args.get("column"), args.get("mode", "frequency")
    lines = []
    for cl in _order(r):
        v = r[cl]
        if mode == "coverage":
            lines.append(f"{cl}: {_f(v['with'])} features with {col}, {_f(v['without'])} without "
                         f"({_pct(v['fraction_without'])})")
        elif mode == "list":
            lines.append(f"{cl}: {_f(v['n'])} features with {col}"
                         + (f", e.g. {', '.join(map(str, v['first'][:3]))}" if v["first"] else ""))
        else:
            top = list(v["top"].items())[:3]
            lines.append(f"{cl}: most common {col} " + (", ".join(f"{k} ({n})" for k, n in top) or "none"))
    return lines


RULES = {
    "filter_level3": _filter_level3,
    "llm_search": _llm_search,
    "select_by_feature_lookup": _select_by_feature_lookup,
    "describe_level3": _describe_level3,
}
