"""Overall shape of a mean curve: the simple function that fits it best.

Candidate functions, with u = 0..1 the position inside the fitted time range:

    flat         y = a                          flat
    linear       y = a + b t                    increase / decrease
    quadratic    y = a + b u + c u^2            U / n when both arms are a visible part of it
    early        y = a + b exp(-k u)            L (early drop, then flat) / early_rise
    late         y = a + b exp(-k (1 - u))      J (flat, then late rise) / late_drop
    bump         y = a + b exp(-((t - m) / w)^2)   peak / valley: a narrow n or U at time m
    step         y = a + b / (1 + exp(-(t - m) / w))   step_up / step_down: two levels, change at m

The fit uses the measured points only and is a function of time, so it also
gives a value where a timepoint is missing (`Fit.predict`).
"""

from dataclasses import dataclass, field

import numpy as np

from .thresholds import DEFAULT

MIN_POINTS = 3           # fewer measured points have no shape
_RATES = (2.0, 4.0, 8.0)   # k of the early / late functions: from a soft bend to a sharp corner
_WIDTHS = (0.6, 1.0)     # w of the bump, in units of the median time step
_STEP = 0.25             # w of the step, in units of the median time step: the change takes one interval
_SIMPLER = 0.02          # the line wins unless a curved function is better by this much adjusted R^2

OPPOSITE_OF = {"increase": "decrease", "U": "n", "L": "early_rise", "J": "late_drop", "peak": "valley",
               "step_up": "step_down"}
OPPOSITE_OF.update({v: k for k, v in list(OPPOSITE_OF.items())})


@dataclass(frozen=True)
class Fit:
    model: str          # flat | linear | quadratic | early | late | bump | step | none
    shape: str          # flat | increase | decrease | U | n | L | early_rise | J | late_drop | peak | valley
                        # | step_up | step_down | irregular (no function fits well) | unknown (too few points)
    r2: float           # share of the curve's variance the function explains
    fits: bool          # r2 reaches th.fit_r2 (always true for flat)
    n_points: int       # measured points the fit is based on
    start: float        # first and last fitted time
    end: float
    at: float = None    # time of the turning point (U, n), the peak / valley, or the step
    params: dict = field(default_factory=dict)

    def predict(self, times):
        """Value of the fitted function at any times, measured or not."""
        t = np.asarray(times, dtype=float)
        p, span = self.params, (self.end - self.start) or 1.0
        u = (t - self.start) / span
        if self.model == "linear":
            return p["a"] + p["b"] * u
        if self.model == "quadratic":
            return p["a"] + p["b"] * u + p["c"] * u ** 2
        if self.model == "early":
            return p["a"] + p["b"] * np.exp(-p["k"] * u)
        if self.model == "late":
            return p["a"] + p["b"] * np.exp(-p["k"] * (1 - u))
        if self.model == "bump":
            return p["a"] + p["b"] * np.exp(-((t - p["m"]) / p["w"]) ** 2)
        if self.model == "step":
            return p["a"] + p["b"] / (1 + np.exp(-(t - p["m"]) / p["w"]))
        return np.full(t.shape, p.get("a", np.nan))

    def as_dict(self):
        return {"model": self.model, "shape": self.shape, "r2": self.r2, "fits": self.fits,
                "n_points": self.n_points, "at": self.at}


def _candidates(t, u, n):
    """(model, curved parameters besides the intercept, extra parameters, design columns)."""
    out = [("linear", 1, {}, [u])]
    if n - 3 < 1:      # a curved function needs a point to spare
        return out
    out.append(("quadratic", 2, {}, [u, u ** 2]))
    for k in _RATES:
        out.append(("early", 2, {"k": k}, [np.exp(-k * u)]))
        out.append(("late", 2, {"k": k}, [np.exp(-k * (1 - u))]))
    step = float(np.median(np.diff(t)))
    widths = _WIDTHS if n - 4 >= 1 else _WIDTHS[:1]      # searching the width costs a parameter
    for m in t[1:-1]:
        for w in widths:
            out.append(("bump", 1 + len(widths), {"m": float(m), "w": w * step},
                        [np.exp(-((t - m) / (w * step)) ** 2)]))
    for m in (t[1:-2] + t[2:-1]) / 2:      # a change in the first or last interval is an L or a J
        out.append(("step", 2, {"m": float(m), "w": _STEP * step}, [1 / (1 + np.exp(-(t - m) / (_STEP * step)))]))
    return out


def _name(model, p, predict, th):
    if model == "linear":
        return ("increase" if p["b"] > 0 else "decrease"), None
    if model == "quadratic":
        turn = -p["b"] / (2 * p["c"]) if p["c"] else np.inf
        first, last = predict(np.array([0.0, 1.0]))
        if 0 < turn < 1:
            # a U or an n needs both arms; a short hook at one end is a bent rise or fall
            low = float(predict(np.array([turn]))[0])
            arms = (abs(first - low), abs(last - low))
            if min(arms) >= th.peak_prominence * max(arms):
                return ("U" if p["c"] > 0 else "n"), turn
        return ("increase" if last > first else "decrease"), None
    if model == "step":
        return ("step_up" if p["b"] > 0 else "step_down"), p["m"]
    if model == "early":
        return ("L" if p["b"] > 0 else "early_rise"), None
    if model == "late":
        return ("J" if p["b"] > 0 else "late_drop"), None
    return ("peak" if p["b"] > 0 else "valley"), p["m"]


def fit_curve(y, axis, th=DEFAULT):
    """Fit the candidate functions to one curve `y` over `axis` and keep the best.

    A curve that moves less than th.flat_range is flat. Otherwise the function
    with the highest adjusted R^2 wins, and the straight line is kept unless a
    curved one is clearly better. When the winner explains less than th.fit_r2
    of the variance the shape is "irregular": no simple function describes it.
    Missing points are left out of the fit.
    """
    y = np.asarray(y, dtype=float)
    t = np.asarray(axis.times, dtype=float)
    ok = ~np.isnan(y)
    y, t = y[ok], t[ok]
    order = np.argsort(t)
    y, t = y[order], t[order]
    n = len(y)
    if n < MIN_POINTS or np.ptp(t) == 0:
        return Fit("none", "unknown", 0.0, False, n, float(t.min()) if n else 0.0, float(t.max()) if n else 0.0)
    start, end = float(t[0]), float(t[-1])
    if float(np.ptp(y)) < th.flat_range:
        return Fit("flat", "flat", 1.0, True, n, start, end, params={"a": float(y.mean())})

    u = (t - start) / (end - start)
    total = float(((y - y.mean()) ** 2).sum())
    best = line = None
    for model, p, extra, cols in _candidates(t, u, n):
        design = np.column_stack([np.ones(n)] + cols)
        coef = np.linalg.lstsq(design, y, rcond=None)[0]
        r2 = 1.0 - float(((y - design @ coef) ** 2).sum()) / total
        adj = 1.0 - (1.0 - r2) * (n - 1) / (n - p - 1)
        params = {**dict(zip("abc", (float(c) for c in coef))), **extra}
        found = (adj, r2, model, params)
        if model == "linear":
            line = found
        if best is None or adj > best[0]:
            best = found
    if line[0] >= best[0] - _SIMPLER:
        best = line
    _, r2, model, params = best
    fitted = Fit(model, "", r2, r2 >= th.fit_r2, n, start, end, params=params)
    shape, at = _name(model, params, lambda uu: fitted.predict(start + uu * (end - start)), th)
    if at is not None and model == "quadratic":
        at = start + at * (end - start)
    return Fit(model, shape if fitted.fits else "irregular", r2, fitted.fits, n, start, end,
               at=None if at is None else float(at), params=params)
