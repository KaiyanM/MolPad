"""Step-to-step changes of a mean curve: biggest rise and fall, turning points, volatility."""

import numpy as np


def changes(y, axis):
    """Where the curve `y` moves most between consecutive timepoints."""
    y = np.asarray(y, dtype=float)
    keep = [i for i in range(len(y)) if not np.isnan(y[i])]
    if len(keep) < 2:
        return {"n_steps": 0}
    v = y[keep]
    labels = [axis.labels[i] for i in keep]
    times = np.array([axis.times[i] for i in keep])
    steps = np.diff(v)
    rate = steps / np.where(np.diff(times) == 0, 1, np.diff(times))

    def step(i):
        return {"from": labels[i], "to": labels[i + 1], "change": float(steps[i]),
                "per_time_unit": float(rate[i])}

    signs = np.sign(steps[steps != 0])
    up, down = int(steps.argmax()), int(steps.argmin())
    return {
        "n_steps": int(len(steps)),
        "largest_rise": step(up) if steps[up] > 0 else None,
        "largest_fall": step(down) if steps[down] < 0 else None,
        "turning_points": int((np.diff(signs) != 0).sum()),   # times the direction flips
        "volatility": float(np.abs(steps).mean()),            # mean absolute step
    }
