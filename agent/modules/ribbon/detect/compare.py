"""Relation between two mean curves: opposite, similar, shifted, diverging, converging.

Each curve is replaced by its fitted function (see fit.py), which stands for
its overall shape. The two functions are then read on a common grid, so the
curves may have different or missing timepoints. They may be two groups over
the same time (two clusters, or one cluster in two sample groups), or two
stretches of time of one curve.
"""

import numpy as np
from scipy.stats import spearmanr

from .fit import OPPOSITE_OF, fit_curve
from .thresholds import DEFAULT

TOOLS = ("opposite", "similar", "shifted", "diverging", "converging")
GRID = 25      # points at which the two fitted functions are read


def window(axis, start=None, end=None):
    """Indices of the timepoints of `axis` with start <= time <= end (either may be None)."""
    return [i for i, t in enumerate(axis.times)
            if (start is None or t >= start - 1e-9) and (end is None or t <= end + 1e-9)]


def _r(a, b):
    if len(a) < 3 or np.ptp(a) < 1e-12 or np.ptp(b) < 1e-12:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _lag(a, b, step):
    """Best correlation after sliding one curve along the other by up to half the grid.

    `leader` is the curve whose shape comes first, `by` the shift in grid units.
    """
    best = None
    for k in range(1, len(a) // 2 + 1):
        for leader, r in (("b", _r(a[k:], b[:-k])), ("a", _r(a[:-k], b[k:]))):
            if r is not None and (best is None or r > best["r"]):
                best = {"by": k * step, "r": r, "leader": leader}
    return best


def _direction(v, th):
    """+1 when the values only rise, -1 when they only fall, by at least th.flat_range; else 0."""
    steps, net = np.diff(v), float(v[-1] - v[0])
    tol = 1e-6 * (abs(net) or 1.0)
    if net >= th.flat_range and (steps >= -tol).all():
        return 1
    if net <= -th.flat_range and (steps <= tol).all():
        return -1
    return 0


def _range(given, fitted):
    start, end = given or (None, None)
    return (fitted.start if start is None else float(start), fitted.end if end is None else float(end))


def compare(ya, axis_a, yb, axis_b, on="time", range_a=None, range_b=None, th=DEFAULT):
    """How curve `a` relates to curve `b`, judged on their fitted functions.

    on = "time"      read both functions over the time they share; for two groups in one period
    on = "position"  read each from the start to the end of its own stretch; for two time windows
    range_a/b        (start, end) time of the stretch of each curve; default: all it was fitted on

    relations (any that hold)
        opposite    the fitted functions mirror each other (r <= -th.compare_r), or one
                    only rises while the other only falls
        similar     they follow the same course (r >= th.compare_r), or both are flat
        shifted     the same course, but one comes later: r is not high as they stand
                    and reaches th.compare_r after sliding one along the other
        diverging   the gap between them grows steadily over the grid
        converging  the gap shrinks steadily

    opposite, similar and shifted compare shapes, so the level of the curves
    does not matter. A curve has no shape to compare when no function fits it
    (irregular) or when its function is flat over the stretch that is read.
    """
    fa, fb = fit_curve(ya, axis_a, th), fit_curve(yb, axis_b, th)
    ra, rb = _range(range_a, fa), _range(range_b, fb)
    out = {"on": on, "fit_a": fa.as_dict(), "fit_b": fb.as_dict(), "r": None, "relations": [],
           "flat": [fa.shape == "flat", fb.shape == "flat"]}
    if on == "time":
        lo, hi = max(ra[0], rb[0]), min(ra[1], rb[1])
        ra = rb = (lo, hi)
    if "unknown" in (fa.shape, fb.shape) or ra[1] <= ra[0] or rb[1] <= rb[0]:
        return out

    ga, gb = np.linspace(ra[0], ra[1], GRID), np.linspace(rb[0], rb[1], GRID)
    a, b = fa.predict(ga), fb.predict(gb)
    # a function can be flat on one stretch only, like the foot of an L
    flat = [bool(np.ptp(a) < th.flat_range), bool(np.ptp(b) < th.flat_range)]
    way = [_direction(a, th), _direction(b, th)]
    x = ga if on == "time" else np.linspace(0.0, 1.0, GRID)
    r = _r(a, b)
    gap = np.abs(a - b)
    gap_rho = float(spearmanr(x, gap)[0]) if np.ptp(gap) > 1e-12 else 0.0
    gap_change = float(gap[-1] - gap[0])
    lag = _lag(a, b, float(x[1] - x[0]))
    out.update({
        "range_a": [float(v) for v in ra], "range_b": [float(v) for v in rb], "flat": flat,
        "r": r,                                         # Pearson r of the two fitted functions
        "direction": way,                               # +1 only rises, -1 only falls, 0 neither
        "mirror_shapes": OPPOSITE_OF.get(fa.shape) == fb.shape,   # by name, e.g. U against n
        "lag": lag,
        "gap": {"start": float(gap[0]), "end": float(gap[-1]), "rho": gap_rho},
    })

    rel = []
    shaped = fa.fits and fb.fits and not (flat[0] or flat[1])
    if shaped and ((r is not None and r <= -th.compare_r) or way[0] * way[1] == -1):
        rel.append("opposite")
    if (fa.fits and fb.fits and all(flat)) or (shaped and r is not None and r >= th.compare_r):
        rel.append("similar")
    if (shaped and lag and "similar" not in rel and lag["r"] >= th.compare_r
            and lag["r"] - (r or 0.0) >= th.shift_gain):
        rel.append("shifted")
    if fa.fits and fb.fits:
        if gap_rho >= th.trend_rho - 1e-9 and gap_change >= th.flat_range:
            rel.append("diverging")
        if gap_rho <= -th.trend_rho + 1e-9 and gap_change <= -th.flat_range:
            rel.append("converging")
    out["relations"] = rel
    return out


def strength(result, tool):
    """How strongly `tool` holds, for ranking; higher is stronger. None when it cannot be measured."""
    if tool not in TOOLS:
        raise ValueError(f"unknown comparison tool '{tool}'; choose from {TOOLS}")
    if result.get("r") is None:
        return None
    if tool == "opposite":
        return -result["r"]
    if tool == "similar":
        return result["r"]
    if tool == "shifted":
        return result["lag"]["r"] if result.get("lag") else None
    change = result["gap"]["end"] - result["gap"]["start"]
    return change if tool == "diverging" else -change
