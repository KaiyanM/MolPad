"""Trend of a mean curve: increase, decrease, even or mixed."""

import numpy as np
from scipy.stats import spearmanr

from .thresholds import DEFAULT


def trend(y, axis, th=DEFAULT):
    """Direction and strength of the trend of one curve `y` over `axis`.

    direction
        even      the curve moves less than th.flat_range from bottom to top
        increase  it rises steadily (Spearman rho against time >= th.trend_rho)
        decrease  it falls steadily (rho <= -th.trend_rho)
        mixed     it moves, but not in one direction
    """
    y = np.asarray(y, dtype=float)
    t = np.asarray(axis.times, dtype=float)
    ok = ~np.isnan(y)
    y, t = y[ok], t[ok]
    if len(y) < 2:
        return {"direction": "unknown", "n_points": int(len(y))}

    span = float(y.max() - y.min())
    rho = float(spearmanr(t, y)[0]) if len(y) > 2 and span > 0 else float(np.sign(y[-1] - y[0]))
    slope = float(np.polyfit(t, y, 1)[0]) if np.ptp(t) > 0 else 0.0
    steps = np.diff(y)

    if span < th.flat_range:
        direction = "even"
    elif rho >= th.trend_rho - 1e-9:      # rho is a ratio of sums; allow for rounding
        direction = "increase"
    elif rho <= -th.trend_rho + 1e-9:
        direction = "decrease"
    else:
        direction = "mixed"
    return {
        "direction": direction,
        "rho": rho,                                    # rank correlation with time, -1..1
        "slope": slope,                                # least-squares change per unit of time
        "net_change": float(y[-1] - y[0]),             # last minus first
        "range": span,                                 # max minus min of the curve
        "share_rising_steps": float((steps > 0).mean()) if len(steps) else 0.0,
        "monotonic": bool((steps >= 0).all() or (steps <= 0).all()),
        "n_points": int(len(y)),
    }
