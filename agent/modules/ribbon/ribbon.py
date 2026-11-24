"""A ribbon: one cluster in one sample group, as the ribbon plot draws it.

Everything the agent says about a ribbon (the mean curve, its shape and peak, the fitted
function, the width of the band) is read from one object, built once by the detectors in
the detectors in detect/. Operations on ribbons say what they need: when a question leaves a needed
input out, the operation raises MissingInput with the choices and a default, and the caller
decides whether to assume the default (and say so) or to ask.

    Ribbon.from_values(...)       build from a feature matrix
    ribbon.describe()             the dict describe_pattern reports
    ribbon.similarity(other)      do two ribbons of one sample group follow the same curve?
    similar_clusters(...)         clusters whose ribbons are similar to those of a base cluster
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ...core.session import MissingInput
from . import detect as patterns
from .detect.thresholds import DEFAULT

MATCH = ("all", "any")   # similar in every sample group read | in at least one


@dataclass(frozen=True)
class Ribbon:
    cluster: str
    subject: str                    # sample group
    labels: tuple                   # timepoint columns, in time order
    times: tuple                    # their numeric times
    mean: tuple                     # mean curve
    shape: str                      # even | increase | decrease | hump | dip | multi-peak | mixed
    peak: Optional[str]             # timepoint of the highest mean; None for an even curve
    n_peaks: int
    fitted_shape: str               # flat | J | L | U | n | peak | ... (detect/fit.py)
    fit_r2: Optional[float]
    width_mean: Optional[float]     # ribbon width (max - min of the features), mean over time
    width_max: Optional[float]
    width_area: Optional[float]
    width_trend: Optional[str]      # expanding | contracting | steady | mixed
    n_features: int
    fraction_constant: float
    text: str = field(repr=False, default="")

    @classmethod
    def from_values(cls, cluster, subject, matrix, labels, times=None, groups=None,
                    expected_times=None, th=DEFAULT):
        """matrix: rows = features of the cluster, columns = the timepoints of the sample group."""
        m = np.asarray(matrix, dtype=float)
        d = patterns.describe(m, labels, times=times, groups=groups, expected_times=expected_times, th=th)
        axis = patterns.TimeAxis.of(labels, times)
        rb = d["ribbon"] or {}
        return cls(
            cluster=str(cluster), subject=str(subject), labels=tuple(labels),
            times=tuple(float(t) for t in axis.times), mean=tuple(float(v) for v in d["mean"].values()),
            shape=d["shape"], peak=None if d["shape"] == "even" else d["peaks"]["highest"]["at"],
            n_peaks=d["peaks"]["n_peaks"], fitted_shape=d["fit"]["shape"], fit_r2=d["fit"]["r2"],
            width_mean=d["spread"]["ribbon_width"]["mean"], width_max=rb.get("width", {}).get("max"),
            width_area=rb.get("width", {}).get("area"), width_trend=rb.get("trend", {}).get("direction"),
            n_features=int(len(m)), fraction_constant=d["missingness"]["fraction_constant"], text=d["text"])

    def describe(self):
        """The fields a pattern description reports (Session.describe_pattern)."""
        return {"shape": self.shape, "peak": self.peak, "n_peaks": self.n_peaks,
                "fitted_shape": self.fitted_shape, "fit_r2": self.fit_r2,
                "mean": [round(v, 2) for v in self.mean],
                "ribbon_width": self.width_mean, "ribbon_max_width": self.width_max,
                "ribbon_area": self.width_area, "ribbon_trend": self.width_trend,
                "fraction_constant_features": self.fraction_constant, "text": self.text}

    def similarity(self, other, th=DEFAULT):
        """Do the two mean curves follow the same course? Both must be of one sample group.

        Judged on the fitted functions (detect/compare): similar when their Pearson r is at
        least th.compare_r, or when both are flat. Returns
        {"similar", "r", "shape_a", "shape_b", "both_flat", "note"}; r is None when a curve has
        no shape to correlate (flat, or no timepoints).
        """
        if self.subject != other.subject:
            raise ValueError(f"similarity compares ribbons of one sample group, got {self.subject} "
                             f"and {other.subject}")
        r = patterns.compare(np.asarray(self.mean), patterns.TimeAxis.of(self.labels, self.times),
                             np.asarray(other.mean), patterns.TimeAxis.of(other.labels, other.times),
                             "time", th=th)
        sa, sb = r["fit_a"]["shape"], r["fit_b"]["shape"]
        both_flat = all(r["flat"])
        note = "both flat" if both_flat else f"{sa} vs {sb}" + (f", r = {r['r']:.2f}" if r["r"] is not None else "")
        return {"similar": "similar" in r["relations"], "r": r["r"], "shape_a": sa, "shape_b": sb,
                "both_flat": both_flat, "note": note}


def similarity_metric(th=DEFAULT):
    return ("each cluster mean curve is replaced by the simple function that fits it best "
            f"(line, U / n, L / J, peak / valley, step; R2 >= {th.fit_r2}); two clusters are similar in a "
            f"sample group when the Pearson r of their fitted functions >= {th.compare_r}, or both are flat")


def similar_clusters(ribbons, base, subjects=None, match=None, top_n=None, th=DEFAULT):
    """Clusters whose ribbons follow the same curve as those of the `base` cluster(s).

    ribbons   {cluster: {subject: Ribbon}}
    base      the cluster(s) the others are compared with; with several, a cluster must be
              similar to each of them
    subjects  the sample groups to read; default: every one the ribbons have
    match     all: similar in every sample group read | any: in at least one. A sample group
              name is also accepted and means "read only that one".

    With more than one sample group to read, `match` must be given: MissingInput otherwise.
    The result always holds the per-sample-group answer too, so an empty "all" can still say
    where the curves do agree.
    """
    base = [b for b in base if b in ribbons]
    if not base:
        raise ValueError("similarity needs the cluster to compare with: pick it first")
    names = list(subjects or next(iter(ribbons.values())).keys())
    if match in names:
        names, match = [match], None
    if len(names) > 1 and match is None:
        raise MissingInput(
            "match", list(MATCH) + names, "all", "similarity over several sample groups",
            say=f'"similar" was read as similar in every sample group ({" and ".join(names)}). Ask for '
                + ", ".join(f'"in {s}"' for s in names) + ' or "in at least one sample group" to change this.')
    if match is not None and match not in MATCH:
        raise ValueError(f"unknown match '{match}'; choose from {', '.join(MATCH)}")
    match = match or "all"

    others = [c for c in ribbons if c not in base]
    pairs, per_subject = {}, {s: [] for s in names}
    for c in others:
        pairs[c] = {}
        for s in names:
            sims = [ribbons[b][s].similarity(ribbons[c][s], th) for b in base
                    if s in ribbons[b] and s in ribbons[c]]
            ok = bool(sims) and all(x["similar"] for x in sims)
            rs = [x["r"] for x in sims if x["r"] is not None]
            pairs[c][s] = {"similar": ok, "r": min(rs) if rs else None,
                           "note": "; ".join(x["note"] for x in sims) or "not measured"}
            if ok:
                per_subject[s].append(c)

    def keep(c):
        hits = [pairs[c][s]["similar"] for s in names]
        return all(hits) if match == "all" else any(hits)

    def score(c):   # a correlated pair ranks above a pair that is only flat on both sides
        rs = [pairs[c][s]["r"] for s in names if pairs[c][s]["similar"] and pairs[c][s]["r"] is not None]
        return -round(sum(rs) / len(names), 6) if rs else 0.0

    picked = sorted((c for c in others if keep(c)), key=score)   # stable: ties keep dashboard order
    return {"base": base, "subjects": names, "match": match, "metric": similarity_metric(th),
            "clusters": picked[:top_n] if top_n else picked,
            "similar_per_subject": per_subject, "value_per_cluster": pairs}
