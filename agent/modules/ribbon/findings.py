"""What the data operations of the ribbon plot found, as short text lines (agent/findings.py)."""

from ...core.text import _f, _groups, _list, _order, _pct


def _select_by_pattern(args, r):
    lines = [f"metric: {r['metric']}"] + _groups(r, args.get("criterion"))
    if "value_per_cluster" in r:                       # colour divergence ranks every cluster
        v = r["value_per_cluster"]
        lines.append("values: " + ", ".join(f"{c} {_f(v[c])}" for c in list(v)[:5]))
        if r.get("lines_by"):
            lines.append(f"the lines are grouped by {r['lines_by'].replace('level', 'level ')}, as on the page")
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


def _select_by_similarity(args, r):
    base, names = ", ".join(r["base"]), r["subjects"]
    lines = [f"metric: {r['metric']}"]
    if len(names) > 1:
        lines.append(f"similar to {base} in {'every one of' if r['match'] == 'all' else 'at least one of'} "
                     f"{', '.join(names)}: {_list(r['clusters'])}")
    pairs = r["value_per_cluster"]
    for s in names:
        hits = r["similar_per_subject"].get(s) or []
        lines.append(f"similar to {base} in {s}: "
                     + (", ".join(f"{c} ({pairs[c][s]['note']})" for c in _order(hits)) or "none"))
    return lines


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


RULES = {
    "select_by_pattern": _select_by_pattern,
    "select_by_ribbon": _select_by_ribbon,
    "select_by_comparison": _select_by_comparison,
    "select_by_similarity": _select_by_similarity,
    "describe_pattern": _describe_pattern,
}
