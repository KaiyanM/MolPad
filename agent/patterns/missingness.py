"""Missing data in a feature x timepoint matrix: which timepoints, how often."""

import numpy as np

from .thresholds import DEFAULT


def missingness(matrix, axis, missing_value=None, expected_times=None, th=DEFAULT):
    """Missing values per timepoint and per feature, plus gaps in the time axis.

    matrix          rows = features, columns = timepoints
    missing_value   a number that also means "not measured" (for example 0 in raw counts)
    expected_times  the full list of times, to report timepoints the axis lacks

    A feature whose values are all the same carries no pattern (after row
    standardisation an undetected feature looks like this), so constant
    features are counted as well.
    """
    m = np.asarray(matrix, dtype=float)
    if m.ndim != 2:
        raise ValueError("matrix must be features x timepoints")
    miss = np.isnan(m)
    if missing_value is not None:
        miss |= m == missing_value
    n, k = m.shape
    per_tp = miss.sum(axis=0)
    per_feature = miss.sum(axis=1)
    with np.errstate(all="ignore"):
        spread = np.where(n and k, np.nanmax(m, axis=1) - np.nanmin(m, axis=1), np.nan) if n else np.array([])
    constant = int((spread < th.constant_tol).sum()) if n else 0
    worst = int(per_tp.argmax()) if n and per_tp.max() > 0 else None
    return {
        "n_features": int(n),
        "n_timepoints": int(k),
        "fraction_missing": float(miss.mean()) if miss.size else 0.0,
        "per_timepoint": {axis.labels[i]: {"n": int(per_tp[i]),
                                           "fraction": float(per_tp[i] / n) if n else 0.0}
                          for i in range(k)},
        "most_missing_timepoint": axis.labels[worst] if worst is not None else None,
        "features_complete": int((per_feature == 0).sum()),
        "features_with_missing": int((per_feature > 0).sum()),
        "features_all_missing": int((per_feature == k).sum()),
        "features_constant": constant,
        "fraction_constant": float(constant / n) if n else 0.0,
        "absent_timepoints": axis.gaps(expected_times),   # times the axis itself lacks
    }
