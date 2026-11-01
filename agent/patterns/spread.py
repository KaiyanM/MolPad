"""Spread of the features around the mean curve: the width of the ribbon."""

import numpy as np

from .thresholds import DEFAULT
from .width import width as ribbon_width


def spread(matrix, axis, th=DEFAULT):
    """How far the features are from each other at each timepoint.

    ribbon_width   max - min of the features (what the ribbon plot draws; see width.py)
    sd, iqr        less sensitive to single extreme features
    consistency    mean correlation of each feature with the mean curve:
                   near 1 when the features follow the same trajectory
    """
    m = np.asarray(matrix, dtype=float)
    n = m.shape[0]
    if n == 0:
        return {"n_features": 0}
    with np.errstate(all="ignore"):
        sd = np.nanstd(m, axis=0, ddof=1) if n > 1 else np.zeros(m.shape[1])
        iqr = np.nanpercentile(m, 75, axis=0) - np.nanpercentile(m, 25, axis=0)
        mean = np.nanmean(m, axis=0)

    # correlation of each feature with the mean curve (constant features have none)
    centred = m - np.nanmean(m, axis=1, keepdims=True)
    mc = mean - np.nanmean(mean)
    num = np.nansum(centred * mc, axis=1)
    den = np.sqrt(np.nansum(centred ** 2, axis=1) * np.nansum(mc ** 2))
    with np.errstate(all="ignore"):
        r = num[den > 0] / den[den > 0]
    consistency = float(r.mean()) if len(r) else None

    w = ribbon_width(m, axis)

    def per(v):
        return {axis.labels[i]: float(v[i]) for i in range(len(axis))}

    return {
        "n_features": int(n),
        "ribbon_width": {k: w[k] for k in ("mean", "per_timepoint", "widest_at", "narrowest_at")},
        "sd": {"mean": float(np.nanmean(sd)), "per_timepoint": per(sd),
               "largest_at": axis.labels[int(np.nanargmax(sd))],
               "smallest_at": axis.labels[int(np.nanargmin(sd))]},
        "iqr": {"mean": float(np.nanmean(iqr))},
        "consistency": consistency,
        "consistent": bool(consistency is not None and consistency >= th.consistent_r),
        "share_above_mean_trend": float((r > 0).mean()) if len(r) else None,   # features moving with the mean
    }
