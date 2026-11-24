"""How far apart the mean lines of sub-groups are (the coloured lines of one ribbon panel)."""

import numpy as np


def divergence(matrix, groups, axis):
    """Gap between the highest and the lowest sub-group mean at each timepoint.

    matrix   rows = features, columns = timepoints
    groups   one label per feature (for example its phylum)
    """
    m = np.asarray(matrix, dtype=float)
    groups = np.asarray(groups)
    names = [g for g in dict.fromkeys(groups.tolist()) if g is not None and g == g]
    if len(names) < 2:
        return {"n_groups": len(names), "mean_gap": 0.0}
    with np.errstate(all="ignore"):
        lines = np.vstack([np.nanmean(m[groups == g], axis=0) for g in names])
    gap = np.nanmax(lines, axis=0) - np.nanmin(lines, axis=0)
    i = int(np.nanargmax(gap))
    return {
        "n_groups": len(names),
        "mean_gap": float(np.nanmean(gap)),
        "largest_gap": {"at": axis.labels[i], "gap": float(gap[i]),
                        "highest": str(names[int(np.nanargmax(lines[:, i]))]),
                        "lowest": str(names[int(np.nanargmin(lines[:, i]))])},
        "per_timepoint": {axis.labels[k]: float(gap[k]) for k in range(len(axis))},
        "group_sizes": {str(g): int((groups == g).sum()) for g in names},
    }
