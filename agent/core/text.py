"""Small helpers for writing findings lines: numbers, percentages, cluster lists in dashboard order."""

import re


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
