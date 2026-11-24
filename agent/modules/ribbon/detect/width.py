"""Width of a ribbon: the distance between its upper and lower boundary over time."""

import warnings

import numpy as np


def width(matrix, axis):
    """Width of the ribbon of a group of features at each timepoint, and summaries of it.

    per_timepoint  max - min of the features (what the ribbon plot draws)
    mean, max, min the average, largest and smallest width over the timepoints
    variability    standard deviation of the width over the timepoints, and cv = sd / mean;
                   high when the ribbon swells and narrows over time
    area           width integrated over time (trapezoid rule on axis.times), so uneven
                   spacing between timepoints counts; area_per_time = area / time span
    Timepoints where every feature is missing are skipped.
    """
    m = np.asarray(matrix, dtype=float)
    if m.ndim == 1:
        m = m[None, :]
    if m.shape[0] == 0 or m.shape[1] != len(axis):
        return {"n_timepoints": 0}
    with warnings.catch_warnings():          # a timepoint with no values gives NaN, skipped below
        warnings.simplefilter("ignore", RuntimeWarning)
        w = np.nanmax(m, axis=0) - np.nanmin(m, axis=0)
    ok = ~np.isnan(w)
    if not ok.any():
        return {"n_timepoints": 0}
    t = np.asarray(axis.times, dtype=float)[ok]
    v = w[ok]
    span = float(t.max() - t.min()) if len(t) > 1 else 0.0
    area = float(np.sum((v[1:] + v[:-1]) / 2 * np.diff(t))) if len(v) > 1 else 0.0
    sd = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
    mean = float(v.mean())
    labels = [axis.labels[i] for i in range(len(axis)) if ok[i]]
    return {
        "n_timepoints": int(len(v)),
        "per_timepoint": {labels[i]: float(v[i]) for i in range(len(v))},
        "mean": mean,
        "max": float(v.max()), "widest_at": labels[int(v.argmax())],
        "min": float(v.min()), "narrowest_at": labels[int(v.argmin())],
        "variability": {"sd": sd, "cv": sd / mean if mean > 0 else 0.0},
        "area": area,
        "area_per_time": area / span if span > 0 else mean,
    }
