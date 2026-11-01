"""All detectors on one group of features, plus a plain-text description."""

import numpy as np

from .changes import changes
from .divergence import divergence
from .fit import fit_curve
from .missingness import missingness
from .peaks import peaks
from .ribbon import ribbon
from .spread import spread
from .thresholds import DEFAULT
from .timeaxis import TimeAxis
from .trend import trend


def shape_of(tr, pk):
    """One word for the curve, from its trend and peaks.

    even | increase | decrease | hump (one peak inside) | dip (one trough
    inside) | multi-peak (two or more peaks inside) | mixed
    """
    if tr["direction"] in ("even", "increase", "decrease", "unknown"):
        return tr["direction"]
    if pk.get("n_interior_peaks", 0) >= 2:
        return "multi-peak"
    if pk.get("n_interior_peaks", 0) == 1:
        return "hump"
    if pk.get("n_interior_troughs", 0) >= 1:
        return "dip"
    return "mixed"


def _text(shape, tr, pk, ch, ms, sp, dv, rb=None):
    s = []
    if shape == "unknown":
        return "Too few timepoints to describe."
    if shape == "even":
        s.append(f"Even: the mean moves by only {tr['range']:.2f}.")
    elif shape in ("increase", "decrease"):
        s.append(f"Steady {shape}: net change {tr['net_change']:+.2f}, rank correlation with time {tr['rho']:+.2f}.")
    else:
        s.append(f"{shape.capitalize()}: range {tr['range']:.2f}, net change {tr['net_change']:+.2f}.")
    if shape != "even":
        where = ", ".join(f"{p['at']} ({p['phase']})" for p in pk["peaks"])
        s.append(f"{pk['n_peaks']} peak{'s' if pk['n_peaks'] != 1 else ''}"
                 + (f" at {where}" if where else "") + f"; lowest at {pk['lowest']['at']}.")
        # a step is worth a sentence only when it is a visible part of the curve
        big = 0.1 * tr["range"]
        r, f = ch.get("largest_rise"), ch.get("largest_fall")
        if r and r["change"] >= big:
            s.append(f"Largest rise {r['from']} to {r['to']} ({r['change']:+.2f}).")
        if f and -f["change"] >= big:
            s.append(f"Largest fall {f['from']} to {f['to']} ({f['change']:+.2f}).")
    if sp.get("n_features"):
        w = sp["ribbon_width"]
        c = sp["consistency"]
        s.append(f"Ribbon width {w['mean']:.2f} on average, widest at {w['widest_at']}; "
                 f"feature SD {sp['sd']['mean']:.2f}"
                 + (f"; features {'follow' if sp['consistent'] else 'do not closely follow'} "
                    f"the mean (r = {c:.2f})." if c is not None else "."))
    if rb and rb["trend"]["direction"] in ("expanding", "contracting"):
        w = list(rb["width"]["per_timepoint"].values())
        s.append(f"The ribbon {'widens' if rb['trend']['direction'] == 'expanding' else 'narrows'} "
                 f"over time: width {w[0]:.2f} -> {w[-1]:.2f}.")
    bits = []
    if ms["fraction_missing"] > 0:
        bits.append(f"{ms['fraction_missing']:.1%} of values missing, most at {ms['most_missing_timepoint']}")
    if ms["features_constant"]:
        bits.append(f"{ms['fraction_constant']:.1%} of features are constant")
    if ms["absent_timepoints"]:
        bits.append("no measurement at time " + ", ".join(f"{t:g}" for t in ms["absent_timepoints"]))
    s.append(("Missingness: " + "; ".join(bits) + ".") if bits else "No missing values.")
    if dv and dv.get("n_groups", 0) >= 2:
        g = dv["largest_gap"]
        s.append(f"Sub-group lines are {dv['mean_gap']:.2f} apart on average, most at {g['at']} "
                 f"({g['highest']} above {g['lowest']} by {g['gap']:.2f}).")
    return " ".join(s)


def describe(matrix, labels, times=None, groups=None, missing_value=None, expected_times=None,
             drop_constant=False, th=DEFAULT):
    """Describe one group of features over time.

    matrix          rows = features, columns = timepoints (array or DataFrame values)
    labels          timepoint names, in time order
    times           numeric times; default: the number at the end of each label
    groups          optional label per feature, to measure how sub-group lines diverge
    missing_value   optional number that also counts as missing
    expected_times  optional full list of times, to report absent timepoints
    drop_constant   leave constant features out of the mean, trend, peaks and spread
                    (they are still counted under missingness)

    Returns a dict with keys shape, mean, trend, peaks, changes, missingness,
    spread, ribbon (width measures and width trend, see ribbon.py), fit (the
    fitted function, see fit.py), divergence (when groups are given) and text.
    """
    axis = TimeAxis.of(labels, times)
    m = np.asarray(matrix, dtype=float)
    if m.ndim == 1:
        m = m[None, :]
    if m.shape[1] != len(axis):
        raise ValueError("matrix columns and labels differ in length")
    work = m.copy()
    if missing_value is not None:
        work[work == missing_value] = np.nan
    ms = missingness(m, axis, missing_value, expected_times, th)
    if drop_constant and len(work):
        with np.errstate(all="ignore"):
            varying = (np.nanmax(work, axis=1) - np.nanmin(work, axis=1)) >= th.constant_tol
        work = work[varying]
        groups = np.asarray(groups)[varying] if groups is not None else None
    with np.errstate(all="ignore"):
        mean = np.nanmean(work, axis=0) if len(work) else np.full(len(axis), np.nan)

    tr = trend(mean, axis, th)
    pk = peaks(mean, axis, th)
    ch = changes(mean, axis)
    sp = spread(work, axis, th)
    rb = ribbon(work, axis, th) if len(work) else None
    dv = divergence(work, groups, axis) if groups is not None and len(work) else None
    shape = shape_of(tr, pk)
    ft = fit_curve(mean, axis, th)
    out = {"shape": shape, "mean": {axis.labels[i]: float(mean[i]) for i in range(len(axis))},
           "trend": tr, "peaks": pk, "changes": ch, "missingness": ms, "spread": sp,
           "ribbon": rb, "fit": {**ft.as_dict(), "function": ft}}
    if dv is not None:
        out["divergence"] = dv
    out["text"] = _text(shape, tr, pk, ch, ms, sp, dv, rb)
    if ft.shape not in ("unknown", "flat"):
        out["text"] += (f" Fitted overall shape: {ft.shape} (R2 = {ft.r2:.2f})." if ft.fits
                        else f" No simple function fits the curve (best R2 = {ft.r2:.2f}).")
    return out
