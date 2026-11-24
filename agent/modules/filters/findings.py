"""What the data operations of the filters, and the comparison of two filter settings found, as short text lines (agent/findings.py)."""

from ...core.text import _f, _list, _order


def _filter_cols(args, r):
    return [f"kept sample group {args.get('subject')}: {', '.join(r.get('columns', []))}"]


def _filter_level1(args, r):
    return [f"kept {_f(r['n_features'])} features with level 1 = {args.get('value')}"]


def _filter_level2(args, r):
    return [f"kept {_f(r['n_features'])} features with level 2 in {', '.join(args.get('values', []))}"]


def _compare_variants(args, r):
    """Which clusters are main clusters of each compared value, with the counts of every value.

    'Main cluster of X only' never means the cluster lacks the other value: the counts say so.
    """
    variants, counts = r["variants"], r.get("counts") or {}
    names = list(variants)
    lines = [f"main clusters of {label}: {_list(cl)}" for label, cl in variants.items()]

    def nums(cl):
        c = counts.get(cl)
        return f" ({', '.join(f'{v} {_f(c[v])}' for v in c)})" if c else ""

    for cl in _order(counts or set().union(*variants.values())):
        of = [label for label in names if cl in variants[label]]
        if len(of) == len(names):
            lines.append(f"{cl}: a main cluster of all of {', '.join(names)}{nums(cl)}")
        else:
            rest = [label for label in names if label not in of]
            lines.append(f"{cl}: a main cluster of {', '.join(of)}, not of {', '.join(rest)}{nums(cl)}")
    both = r.get("in_all") or []
    lines.append(f"shared main clusters: {_list(both)}" if both else "no shared main cluster")
    return lines


RULES = {
    "filter_cols": _filter_cols,
    "filter_level1": _filter_level1,
    "filter_level2": _filter_level2,
    "compare_variants": _compare_variants,
}
