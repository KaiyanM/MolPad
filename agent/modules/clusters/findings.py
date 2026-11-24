"""What the data operations of the clusters themselves found, as short text lines (agent/findings.py)."""

from ...core.text import _f, _list, _order, _pct


def _select_by_feature_number(args, r):
    if not r.get("total"):
        return ["no features left after the filters"]
    per = r["features_per_cluster"]
    picked = r["clusters"]
    return [f"rule: {r['rule']}",
            "picked: " + ", ".join(f"{c} ({_f(per[c])} features)" for c in picked),
            f"they hold {_pct(r['share_of_selected'])} of {_f(r['total'])} features"]


def _select_given(args, r):
    return [f"clusters: {_list(r.get('clusters'))}"]


def _select_all(args, r):
    return ["all clusters"]


def _describe_feature_number(args, r):
    per = r["features_per_cluster"]
    return [f"{_f(r['total'])} features; largest {r['largest']} ({_f(per[r['largest']])})",
            "per cluster: " + ", ".join(f"{c} {_f(per[c])}" for c in _order(per))]


RULES = {
    "select_by_feature_number": _select_by_feature_number,
    "select_given": _select_given,
    "select_all": _select_all,
    "describe_feature_number": _describe_feature_number,
}
