"""Findings: a few short lines that say what a data action found. No LLM.

Every data step keeps two things apart:

    findings   these lines, which the message writer reads
    result     the full numbers (the evidence), which the dashboard shows on request

conclude(op, args, result) picks the rule for the data action. Lines name clusters
in dashboard order (Group_1 .. Group_10) and are never cut in the middle: when
they pass FINDINGS_CHARS, whole lines are dropped from the end and a last line
says how many are left in the evidence.
"""

import re

FINDINGS_CHARS = 2000   # per data step, about 500 tokens


def _num(name):
    m = re.search(r"(\d+)$", str(name))
    return (int(m.group(1)) if m else 0, str(name))


def _order(names):
    return sorted(names, key=_num)


def _f(x, digits=2):
    """A number for a line: 2.42, 19.8, 3,412."""
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int) or (isinstance(x, float) and x.is_integer() and abs(x) >= 100):
        return f"{int(x):,}"
    return f"{x:.{digits}g}" if abs(x) >= 10 ** digits else f"{x:.{digits}f}".rstrip("0").rstrip(".")


def _pct(x):
    if x is None:
        return "n/a"
    return f"{100 * x:.1f}%" if 0 < abs(x) < 0.1 else f"{100 * x:.0f}%"


def _list(names):
    return ", ".join(_order(names)) if names else "none"


def _groups(result, default="picked"):
    lines = []
    for g in result.get("groups") or []:
        lines.append(f"{g.get('label') or default}: {_list(g['clusters'])}")
    return lines or ["no cluster fits"]


# ---- filters ---------------------------------------------------------------

def _filter_cols(args, r):
    return [f"kept sample group {args.get('subject')}: {', '.join(r.get('columns', []))}"]


def _filter_level1(args, r):
    return [f"kept {_f(r['n_features'])} features with level 1 = {args.get('value')}"]


def _filter_level2(args, r):
    return [f"kept {_f(r['n_features'])} features with level 2 in {', '.join(args.get('values', []))}"]


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
    return [f"ids for {args.get('concept')} from model knowledge, not looked up: "
            + ", ".join(r.get("ids", []))]


# ---- selectors -------------------------------------------------------------

def _select_by_pattern(args, r):
    lines = [f"metric: {r['metric']}"] + _groups(r, args.get("criterion"))
    if "value_per_cluster" in r:                       # colour divergence ranks every cluster
        v = r["value_per_cluster"]
        lines.append("values: " + ", ".join(f"{c} {_f(v[c])}" for c in list(v)[:5]))
    return lines


def _select_by_ribbon(args, r):
    if r.get("definitions") is None:                   # expanding / contracting
        lines = [f"metric: {r['metric']}"] + _groups(r)
        return lines + [f"read in sample group(s) {', '.join(r.get('subjects', []))}"]
    word = r["criterion"].split("_")[0]
    lines = []
    for m, d in r["definitions"].items():
        v, rank = d["value_per_cluster"], list(d["value_per_cluster"])
        if not rank:
            lines.append(f"{word} by {m.replace('_', ' ')}: no cluster")
            continue
        best = d["ranking"]
        nxt = next((c for c in rank if c not in best), None)
        line = f"{word} by {m.replace('_', ' ')}: {', '.join(best)} ({_f(v[best[0]])}"
        if nxt is not None:
            gap = abs(v[nxt] - v[best[-1]]) / (abs(v[best[-1]]) or 1)
            line += f"; next {nxt}, {_f(v[nxt])}, {_pct(gap)} apart"
        lines.append(line + ")")
    if r.get("definitions_agree") is not None:
        lines.append("the definitions agree" if r["definitions_agree"] else "the definitions disagree")
    lines.append(f"read in sample group(s) {', '.join(r.get('subjects', []))}")
    return lines


def _select_by_comparison(args, r):
    lines = [f"{r['tool']} between {r['between']}"] + _groups(r)
    if r.get("flat_on_one_side"):
        lines.append(f"flat on one side only (no shape to compare): {_list(r['flat_on_one_side'])}")
    return lines


def _select_by_feature_number(args, r):
    if not r.get("total"):
        return ["no features left after the filters"]
    per = r["features_per_cluster"]
    picked = r["clusters"]
    return [f"rule: {r['rule']}",
            "picked: " + ", ".join(f"{c} ({_f(per[c])} features)" for c in picked),
            f"they hold {_pct(r['share_of_selected'])} of {_f(r['total'])} features"]


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
    return lines + _groups(r)


def _components(r):
    sizes = sorted((len(c) for c in r.get("components", [])), reverse=True)
    return f"{r['n_components']} connected components" + (f" (sizes {', '.join(map(str, sizes))})" if sizes else "")


def _select_by_feature_lookup(args, r):
    per = r.get("features_per_cluster") or {}
    if not per:
        return ["no feature matches"]
    return [f"{_f(r['n_features'])} matching features in "
            + ", ".join(f"{c} ({per[c]})" for c in _order(per))]


def _select_examples(args, r):
    lines = [f"{g['label']}: {_list(g['clusters'])} ({g['why']})" for g in r.get("groups") or []]
    return lines or [f"no example cluster for {', '.join(r.get('values') or [])}"]


def _select_given(args, r):
    return [f"clusters: {_list(r.get('clusters'))}"]


def _select_all(args, r):
    return ["all clusters"]


# ---- descriptors -----------------------------------------------------------

def _pattern_line(cl, subject, p):
    bits = [p["shape"]]
    if p.get("peak"):
        bits.append(f"peak {p['peak']}")
    if p.get("fitted_shape") not in (None, "unknown"):
        bits.append(f"fits {p['fitted_shape']} (R2 {_f(p['fit_r2'])})")
    if p.get("ribbon_width") is not None:
        bits.append(f"ribbon width {_f(p['ribbon_width'])}"
                    + (f", {p['ribbon_trend']}" if p.get("ribbon_trend") in ("expanding", "contracting") else ""))
    if (p.get("fraction_constant_features") or 0) >= 0.01:
        bits.append(f"{_pct(p['fraction_constant_features'])} constant features")
    return f"{cl} in {subject}: " + ", ".join(bits)


def _describe_pattern(args, r):
    lines = []
    for part, label in (("cluster", ""), ("filtered_features_only", " (filtered features)")):
        for cl in _order(r.get(part) or {}):
            for subject, p in r[part][cl].items():
                lines.append(_pattern_line(cl, subject, p) + label)
    return lines


def _describe_level2(args, r):
    lines = []
    for cl in _order(r):
        fr = r[cl]["fractions"]
        top = sorted(fr, key=lambda k: -fr[k])[:2]
        within = r[cl].get("within")
        scope = f" kept by the filter ({', '.join(within)})" if within else ""
        lines.append(f"{cl} ({_f(r[cl]['total'])} features{scope}): "
                     + ", ".join(f"{k} {_pct(fr[k])}" for k in top))
    return lines


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


def _describe_feature_number(args, r):
    per = r["features_per_cluster"]
    return [f"{_f(r['total'])} features; largest {r['largest']} ({_f(per[r['largest']])})",
            "per cluster: " + ", ".join(f"{c} {_f(per[c])}" for c in _order(per))]


RULES = {
    "filter_cols": _filter_cols, "filter_level1": _filter_level1, "filter_level2": _filter_level2,
    "filter_level3": _filter_level3, "llm_search": _llm_search,
    "select_by_pattern": _select_by_pattern, "select_by_ribbon": _select_by_ribbon,
    "select_by_comparison": _select_by_comparison, "select_by_feature_number": _select_by_feature_number,
    "select_by_network": _select_by_network, "select_by_feature_lookup": _select_by_feature_lookup,
    "select_given": _select_given, "select_all": _select_all, "select_examples": _select_examples,
    "describe_pattern": _describe_pattern, "describe_level2": _describe_level2,
    "describe_level3": _describe_level3, "describe_weight": _describe_weight,
    "describe_feature_number": _describe_feature_number,
}


def fit(lines, limit=FINDINGS_CHARS):
    """Keep whole lines while they fit in `limit` characters; say how many were left out."""
    kept, used = [], 0
    for i, line in enumerate(lines):
        note = f"... {len(lines) - i} more lines in the evidence"
        if used + len(line) + 1 > limit - (len(note) if i < len(lines) - 1 else 0):
            return kept + [f"... {len(lines) - i} more lines in the evidence"]
        kept.append(line)
        used += len(line) + 1
    return kept


def conclude(op, args, result):
    """Findings of one data action: a short list of plain lines."""
    if isinstance(result, dict) and result.get("error"):
        return [f"failed: {result['error']}"]
    rule = RULES.get(op)
    if rule is None:
        return [f"{op}: no summary rule"]
    try:
        return fit(rule(args or {}, result))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:   # never stop the graph
        return [f"{op}: could not summarise ({type(exc).__name__}: {exc})"]
