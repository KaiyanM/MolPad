"""A ribbon as a whole: its width measures and width trend, and how to rank ribbons by them.

The centerline (the mean curve) is described by trend, peaks, changes and fit; this
module only looks at how wide the ribbon around it is.
"""

import numpy as np

from .thresholds import DEFAULT
from .width import width
from .width_trend import width_trend

# The definitions tried, one answer each, when a question asks for the "tightest" or
# "widest" ribbon without saying how width is measured.
TIGHTNESS = ("mean_width", "max_width", "area")
MEASURES = TIGHTNESS + ("variability", "slope")

METRIC = {
    "mean_width": "mean of the min-max ribbon width over the timepoints",
    "max_width": "largest min-max ribbon width at any timepoint",
    "area": "area between the upper and lower boundary of the ribbon over time (trapezoid rule)",
    "variability": "standard deviation of the ribbon width over the timepoints",
    "slope": "least-squares change of the ribbon width per unit of time",
}


def ribbon(matrix, axis, th=DEFAULT):
    """Width and width trend of the ribbon of one group of features."""
    m = np.asarray(matrix, dtype=float)
    if m.ndim == 1:
        m = m[None, :]
    w = width(m, axis)
    out = {"n_features": int(m.shape[0]), "width": w}
    out["trend"] = (width_trend(w["per_timepoint"], axis, th) if w.get("n_timepoints")
                    else {"direction": "unknown", "n_points": 0})
    return out


def score(result, measure):
    """The value of `measure` for a ribbon() result; None when it cannot be measured."""
    if measure not in MEASURES:
        raise ValueError(f"unknown ribbon measure '{measure}'; choose from {MEASURES}")
    w = result.get("width") or {}
    if not w.get("n_timepoints"):
        return None
    if measure == "mean_width":
        return w["mean"]
    if measure == "max_width":
        return w["max"]
    if measure == "area":
        return w["area"]
    if measure == "variability":
        return w["variability"]["sd"]
    return result["trend"].get("slope")
