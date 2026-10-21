"""Spread of the features around the mean curve: the width of the ribbon."""

import numpy as np

from .thresholds import DEFAULT


def spread(matrix, axis, th=DEFAULT):
    """How far the features are from each other at each timepoint.

    ribbon_width   max - min of the features (what the ribbon plot draws)
    sd, iqr        less sensitive to single extreme features
    consistency    mean correlation of each feature with the mean curve:
                   near 1 when the features follow the same trajectory
    """
    m = np.asarray(matrix, dtype=float)
    n = m.shape[0]
    if n == 0:
        return {"n_features": 0}
    with np.errstate(all="ignore"):
        width = np.nanmax(m, axis=0) - np.nanmin(m, axis=0)
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

    def per(v):
        return {axis.labels[i]: float(v[i]) for i in range(len(axis))}

    return {
        "n_features": int(n),
        "ribbon_width": {"mean": float(np.nanmean(width)), "per_timepoint": per(width),
                         "widest_at": axis.labels[int(np.nanargmax(width))],
                         "narrowest_at": axis.labels[int(np.nanargmin(width))]},
        "sd": {"mean": float(np.nanmean(sd)), "per_timepoint": per(sd),
               "largest_at": axis.labels[int(np.nanargmax(sd))],
               "smallest_at": axis.labels[int(np.nanargmin(sd))]},
        "iqr": {"mean": float(np.nanmean(iqr))},
        "consistency": consistency,
        "consistent": bool(consistency is not None and consistency >= th.consistent_r),
        "share_above_mean_trend": float((r > 0).mean()) if len(r) else None,   # features moving with the mean
    }
