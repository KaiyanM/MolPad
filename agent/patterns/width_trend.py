"""Whether a ribbon expands or contracts over time: the trend of its width."""

from dataclasses import replace

import numpy as np

from .thresholds import DEFAULT
from .trend import trend

NAMES = {"increase": "expanding", "decrease": "contracting", "even": "steady",
         "mixed": "mixed", "unknown": "unknown"}


def width_trend(w, axis, th=DEFAULT):
    """Direction and rate of change of the ribbon width `w` (one value per timepoint of `axis`).

    direction
        steady       the width moves less than th.width_flat from narrowest to widest
        expanding    it grows steadily (Spearman rho against time >= th.trend_rho)
        contracting  it shrinks steadily (rho <= -th.trend_rho)
        mixed        it changes, but not in one direction
    slope is the least-squares change of width per unit of time.
    """
    if isinstance(w, dict):
        w = [w.get(label, np.nan) for label in axis.labels]
    tr = trend(w, axis, replace(th, flat_range=th.width_flat))
    out = {"direction": NAMES[tr["direction"]], "n_points": tr["n_points"]}
    if tr["direction"] != "unknown":
        out.update(slope=tr["slope"], rho=tr["rho"], net_change=tr["net_change"])
    return out
