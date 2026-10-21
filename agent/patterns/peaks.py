"""Peaks and troughs of a mean curve: where they are and how many."""

import numpy as np

from .thresholds import DEFAULT


def _extrema(y):
    """Indices of local maxima, endpoints included. A flat top counts once, at its first point."""
    n, out = len(y), []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and y[j + 1] == y[i]:
            j += 1
        left = i == 0 or y[i - 1] < y[i]
        right = j == n - 1 or y[j + 1] < y[i]
        if left and right and n > 1:
            out.append(i)
        i = j + 1
    return out


def _prominence(y, i):
    """Height of peak i above the lowest point between it and the nearest higher peak.

    With a higher peak on both sides, the higher of the two low points counts.
    Of two equally high peaks the earlier one is treated as the higher.
    """
    def side(idx, beats):
        low = y[i]
        for k in idx:
            if beats(y[k]):
                return float(low), True
            low = min(low, y[k])
        return float(low), False

    left, higher_left = side(range(i - 1, -1, -1), lambda v: v >= y[i])
    right, higher_right = side(range(i + 1, len(y)), lambda v: v > y[i])
    if higher_left and higher_right:
        return float(y[i] - max(left, right))
    if higher_left:
        return float(y[i] - left)
    if higher_right:
        return float(y[i] - right)
    return float(y[i] - min(left, right))


def _find(y, axis, th):
    span = float(np.nanmax(y) - np.nanmin(y))
    found = []
    if span <= 0:
        return found
    for i in _extrema(y):
        prom = _prominence(y, i)
        if prom >= th.peak_prominence * span:
            found.append({"at": axis.labels[i], "time": axis.times[i], "value": float(y[i]),
                          "prominence": prom, "phase": axis.phase(i, th),
                          "interior": 0 < i < len(y) - 1})
    return found


def peaks(y, axis, th=DEFAULT):
    """Peaks and troughs of one curve `y` over `axis`.

    A peak is a local maximum (the first or last point may be one) that stands
    out by at least th.peak_prominence of the curve's range. An even curve
    (range below th.flat_range) has no peaks. Missing points are skipped.
    """
    y = np.asarray(y, dtype=float)
    keep = [i for i in range(len(y)) if not np.isnan(y[i])]
    if len(keep) < 2:
        return {"n_peaks": 0, "n_troughs": 0, "peaks": [], "troughs": []}
    sub = type(axis)(tuple(axis.labels[i] for i in keep), tuple(axis.times[i] for i in keep))
    # phases must refer to the full axis, not the kept points
    full_phase = {axis.labels[i]: axis.phase(i, th) for i in keep}
    v = y[keep]
    even = float(v.max() - v.min()) < th.flat_range
    top = [] if even else _find(v, sub, th)
    bottom = [] if even else _find(-v, sub, th)
    for p in top + bottom:
        p["phase"] = full_phase[p["at"]]
    for p in bottom:
        p["value"] = -p["value"]
    hi, lo = int(v.argmax()), int(v.argmin())
    return {
        "highest": {"at": sub.labels[hi], "value": float(v[hi]), "phase": full_phase[sub.labels[hi]]},
        "lowest": {"at": sub.labels[lo], "value": float(v[lo]), "phase": full_phase[sub.labels[lo]]},
        "n_peaks": len(top),
        "n_interior_peaks": sum(p["interior"] for p in top),
        "peaks": top,
        "n_troughs": len(bottom),
        "n_interior_troughs": sum(p["interior"] for p in bottom),
        "troughs": bottom,
    }
