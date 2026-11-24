"""Data operations of the ribbon plot: the mean curve and the band of a cluster over time."""

import numpy as np

from ...core.dataset import DEFAULT_TOP
from ...core.session import MissingInput, match
from . import detect as patterns
from .ribbon import Ribbon, similar_clusters

TREND_RHO = patterns.Thresholds().trend_rho   # |Spearman rho| at or above this is a steady trend


class Ops:
    """Curves and bands."""

    def _shape(self, values, cols):
        """Trend, peak and a one-word shape for one mean curve (detect/)."""
        axis = self.ds.axis(cols)
        tr = patterns.trend(values, axis)
        pk = patterns.peaks(values, axis)
        return {"mean": [round(float(x), 2) for x in values], "peak": pk["highest"]["at"],
                "trough": pk["lowest"]["at"], "rho": tr["rho"], "shape": patterns.shape_of(tr, pk)}

    def _curves(self, df, subject=None):
        """{cluster: {subject: shape dict}} from the mean of df per cluster."""
        out = {}
        subjects = self._subjects(subject)
        means = df.groupby("cluster")[self.cols].mean()
        for cl, row in means.iterrows():
            out[cl] = {s: self._shape(row[cols].values, cols) for s, cols in subjects.items() if cols}
        return out

    def _colour_column(self):
        """The column the ribbon lines are grouped by on the page; None for one ribbon per cluster."""
        return {"level1": self.cfg.level1, "level2": self.cfg.level2, "type": self.cfg.color,
                "none": None}.get(self.colour_by, self.cfg.level1)

    def _ribbons(self, df, clusters=None, subjects=None):
        """{cluster: {sample group: Ribbon}} for the rows of df (ribbon.py)."""
        all_times = sorted({self.ds.time_of(c) for c in self.ds.timepoints})
        if clusters is not None:
            df = df[df["cluster"].isin(clusters)]
        out = {}
        by = self._colour_column()
        for cl, g in df.groupby("cluster"):
            out[cl] = {s: Ribbon.from_values(cl, s, g[cols].values, cols, times=self.ds.axis(cols).times,
                                             groups=g[by].fillna("(none)").values if by else None,
                                             expected_times=all_times)
                       for s, cols in self._subjects().items() if cols and (not subjects or s in subjects)}
        return {c: out[c] for c in self.ds.clusters if c in out}

    def select_by_pattern(self, criterion, subject=None, timepoint=None, position=None, top_n=None):
        curves = self._curves(self.df, subject)
        order = [c for c in self.ds.clusters if c in curves]

        def all_subjects(cl, shape):
            return all(s["shape"] == shape for s in curves[cl].values())

        if criterion in ("increase", "decrease"):
            groups = [{"label": criterion, "clusters": [c for c in order if all_subjects(c, criterion)]}]
            metric = f"Spearman rho of the cluster mean against time, |rho| >= {TREND_RHO}"
        elif criterion == "increase_and_decrease":
            groups = [{"label": k, "clusters": [c for c in order if all_subjects(c, k)]}
                      for k in ("increase", "decrease")]
            metric = f"Spearman rho of the cluster mean against time, |rho| >= {TREND_RHO}"
        elif criterion == "peak_at":
            def hit(col):
                if timepoint:
                    return col == timepoint
                pos = self.ds.time_position(col)
                th = patterns.Thresholds()
                return {"early": pos <= th.early, "mid": th.early < pos < th.late,
                        "late": pos >= th.late}[position or "mid"]
            # an even curve has no peak worth the name
            picked = [c for c in order
                      if any(s["shape"] != "even" and hit(s["peak"]) for s in curves[c].values())]
            groups = [{"label": f"peak at {timepoint or position or 'mid'}", "clusters": picked}]
            metric = "timepoint of the maximum of the cluster mean, per sample group"
        elif criterion == "color_divergence":
            by = self._colour_column()
            if by is None:
                raise ValueError("the ribbon lines are not coloured by anything now ('Colour lines by' "
                                 "is set to none), so there are no colour lines to compare")
            lines = self.df.groupby(["cluster", self.df[by].fillna("(none)")])[self.cols].mean()
            gap = (lines.groupby("cluster").max() - lines.groupby("cluster").min()).mean(axis=1)
            ranked = gap.sort_values(ascending=False)
            groups = [{"label": f"{criterion} #{i + 1}", "clusters": [c]}
                      for i, c in enumerate(ranked.index[: top_n or DEFAULT_TOP])]
            self._set(groups)
            return {"metric": "mean gap between the highest and lowest colour mean line",
                    "lines_by": self.colour_by,
                    "groups": groups, "value_per_cluster": ranked.round(3).to_dict()}
        else:
            raise ValueError(f"unknown pattern criterion '{criterion}'")

        if top_n:
            groups = [{**g, "clusters": g["clusters"][:top_n]} for g in groups]
        self._set(groups)
        shapes = {c: {s: {"shape": v["shape"], "peak": v["peak"]} for s, v in curves[c].items()} for c in order}
        return {"metric": metric, "groups": groups, "shape_per_cluster": shapes}

    def select_by_ribbon(self, criterion, measure=None, subject=None, top_n=None):
        """Pick clusters by their ribbon in the pattern plot (detect/band).

        The ribbon of each cluster is read per sample group, since the groups share time values.

        tightest_ribbon / widest_ribbon   rank by the ribbon width. measure: mean_width, max_width or
            area; left empty or 'all' it is vague, and each definition in patterns.TIGHTNESS gives
            its own answer. Definitions that pick the same cluster share one group.
        expanding_ribbon / contracting_ribbon   clusters whose width grows (shrinks) steadily in every
            sample group read, steepest first.
        A cluster's width over sample groups is the mean of their mean / max width, and the sum of
        their areas.
        """
        th = patterns.Thresholds()
        subjects = {s: c for s, c in self._subjects(subject).items() if c}
        rb = {}
        for cl, g in self.df.groupby("cluster"):
            rb[cl] = {s: patterns.ribbon(g[cols].values, self.ds.axis(cols), th)
                      for s, cols in subjects.items()}
        order = [c for c in self.ds.clusters if c in rb]

        def value(cl, m):
            v = [patterns.ribbon_score(r, m) for r in rb[cl].values()]
            v = [x for x in v if x is not None]
            if not v:
                return None
            return float(np.sum(v)) if m == "area" else float(np.mean(v))

        per_subject = {c: {s: {"mean_width": r["width"].get("mean"), "max_width": r["width"].get("max"),
                               "area": r["width"].get("area"), "widest_at": r["width"].get("widest_at"),
                               "width_trend": r["trend"]["direction"]}
                           for s, r in rb[c].items()} for c in order}

        if criterion in ("expanding_ribbon", "contracting_ribbon"):
            way = criterion.split("_")[0]
            hits = [c for c in order if all(r["trend"]["direction"] == way for r in rb[c].values())]
            hits.sort(key=lambda c: -abs(value(c, "slope") or 0))
            groups = [{"label": f"{way} ribbon", "clusters": hits[: top_n or len(hits)]}]
            self._set(groups)
            return {"criterion": criterion, "subjects": list(subjects),
                    "metric": f"{patterns.RIBBON_METRIC['slope']}; {way} when the Spearman rho of the "
                              f"width against time is {'>=' if way == 'expanding' else '<= -'}{th.trend_rho} "
                              f"and the width moves by at least {th.width_flat}",
                    "groups": groups, "per_cluster": per_subject}

        if criterion not in ("tightest_ribbon", "widest_ribbon"):
            raise ValueError(f"unknown ribbon criterion '{criterion}'")
        vague = measure in (None, "", "all")
        if not vague and measure not in patterns.TIGHTNESS:
            raise ValueError(f"unknown ribbon measure '{measure}'; choose from {list(patterns.TIGHTNESS)}")
        measures = patterns.TIGHTNESS if vague else (measure,)
        keep = top_n or (1 if vague else DEFAULT_TOP)
        word = criterion.split("_")[0]
        definitions, picks = {}, {}
        for m in measures:
            vals = {c: value(c, m) for c in order}
            ranked = sorted((c for c in order if vals[c] is not None), key=lambda c: vals[c],
                            reverse=(criterion == "widest_ribbon"))
            definitions[m] = {"metric": patterns.RIBBON_METRIC[m], "ranking": ranked[:keep],
                              "value_per_cluster": {c: vals[c] for c in ranked}}
            picks[m] = tuple(ranked[:keep])

        if vague:
            merged = {}           # same pick under several definitions -> one group
            for m in measures:
                merged.setdefault(picks[m], []).append(m.replace("_", " "))
            groups = [{"label": f"{word} by " + (" and ".join(ms) if len(ms) < 3
                                                 else ", ".join(ms[:-1]) + " and " + ms[-1]),
                       "clusters": list(p)}
                      for p, ms in merged.items() if p]
        else:
            groups = [{"label": f"{word} by {measure.replace('_', ' ')} #{i + 1}", "clusters": [c]}
                      for i, c in enumerate(picks[measure])]
        self._set(groups)
        return {"criterion": criterion, "subjects": list(subjects),
                "measure": "all" if vague else measure, "definitions": definitions,
                "definitions_agree": len({picks[m] for m in measures}) == 1 if vague else None,
                "groups": groups,
                "per_cluster": per_subject}

    def _side(self, side, subject):
        """One side of a comparison: the timepoint columns of a sample group and the (start, end)
        time of the stretch that is read; None where the side does not set it."""
        if subject not in self.ds.subjects:
            raise ValueError(f"no sample group '{subject}'; choose from {list(self.ds.subjects)}")

        def time(x):
            return None if x in (None, "") else self.ds.time_of(str(x))

        return self.ds.subjects[subject], (time(side.get("start")), time(side.get("end")))

    def select_by_comparison(self, tool, between="subjects", a=None, b=None, top_n=None):
        """Pick clusters by how two of their mean curves relate (detect/compare).

        Each curve is first replaced by the function fitted to it (detect/fit), over all
        timepoints of its sample group.

        tool      opposite | similar | shifted | diverging | converging
        between   subjects  one cluster in sample group a against the same cluster in sample group b
                  windows   one cluster in time window a against the same cluster in time window b
                  clusters  one cluster against another, over the range of side a
        a, b      {"subject", "start", "end"}: the sample group and the first and last timepoint of
                  each side. Left out, the sides are the first two sample groups, or the first and
                  the second half of the sample group.
        """
        if tool not in patterns.TOOLS:
            raise ValueError(f"unknown comparison tool '{tool}'; choose from {list(patterns.TOOLS)}")
        a, b = dict(a or {}), dict(b or {})
        names = list(self.ds.subjects)
        means = self.df.groupby("cluster")[self.ds.timepoints].mean()
        order = [c for c in self.ds.clusters if c in means.index]
        th = patterns.Thresholds()

        def rel(cl_a, side_a, cl_b, side_b, on):
            (cols_a, range_a), (cols_b, range_b) = side_a, side_b
            return patterns.compare(means.loc[cl_a, cols_a].values, self.ds.axis(cols_a),
                                    means.loc[cl_b, cols_b].values, self.ds.axis(cols_b),
                                    on, range_a, range_b, th)

        def brief(r):
            return {"shape_a": r["fit_a"]["shape"], "shape_b": r["fit_b"]["shape"],
                    "fit_r2": [r["fit_a"]["r2"], r["fit_b"]["r2"]], "flat": r["flat"],
                    "r": r["r"], "direction": r.get("direction"), "relations": r["relations"],
                    "shifted_by": r["lag"]["by"] if "shifted" in r["relations"] else None,
                    "gap_start": r.get("gap", {}).get("start"), "gap_end": r.get("gap", {}).get("end")}

        def ranked(results):
            hits = [k for k, r in results.items() if tool in r["relations"]]
            # rounded, so a tie keeps dashboard order whatever the float noise of the input
            return sorted(hits, key=lambda k: -round(patterns.strength(results[k], tool) or 0, 6))

        def note(r):
            if tool == "shifted":
                return f"r = {r['lag']['r']:.2f} after a shift of {r['lag']['by']:.2g}"
            if tool in ("diverging", "converging"):
                return f"gap {r['gap']['start']:.2f} -> {r['gap']['end']:.2f}"
            if r["r"] is None:      # two flat curves count as similar and have no r
                return "both flat" if all(r["flat"]) else f"{r['fit_a']['shape']} vs {r['fit_b']['shape']}"
            return f"{r['fit_a']['shape']} vs {r['fit_b']['shape']}, r = {r['r']:.2f}"

        def span(side):
            cols, (start, end) = side
            t = self.ds.axis(cols).times
            return [t[0] if start is None else start, t[-1] if end is None else end]

        if between == "clusters":
            subject = a.get("subject") or self.subject
            sides = [subject] if subject else names
            base = [c for c in self.targets if c in order] if 0 < len(self.targets) < len(order) else []
            groups, value = [], {}
            for s in sides:
                side = self._side(a, s)
                pairs = [(x, y) for i, x in enumerate(order) for y in order[i + 1:]
                         if not base or (x in base) != (y in base)]
                res = {p: rel(p[0], side, p[1], side, "time") for p in pairs}
                for p in ranked(res)[: top_n or DEFAULT_TOP]:
                    first, second = (p[1], p[0]) if p[1] in base else p
                    groups.append({"label": f"{tool} in {s} ({note(res[p])})", "clusters": [first, second]})
                value[s] = {f"{x} vs {y}": brief(r) for (x, y), r in res.items()
                            if r["r"] is not None and (tool in r["relations"] or base)}
            self._set(groups)
            return {"tool": tool, "between": between, "metric": self._compare_metric(tool, th),
                    "time_range": {s: span(self._side(a, s)) for s in sides}, "groups": groups,
                    "value_per_pair": value}

        if between == "windows":
            subject = a.get("subject") or b.get("subject") or self.subject or names[0]
            side_a, side_b = self._side(a, subject), self._side(b, subject)
            if not any(v is not None for side in (side_a, side_b) for v in side[1]):
                t = self.ds.axis(side_a[0]).times      # first half against second half
                mid = (t[0] + t[-1]) / 2
                side_a, side_b = (side_a[0], (t[0], mid)), (side_b[0], (mid, t[-1]))
            label, on = f"{tool} in {subject}: time {span(side_a)[0]:g}-{span(side_a)[1]:g} vs " \
                        f"{span(side_b)[0]:g}-{span(side_b)[1]:g}", "position"
        elif between == "subjects":
            sa = a.get("subject") or names[0]
            sb = b.get("subject") or next((s for s in names if s != sa), None)
            if sb is None:
                raise ValueError("the data has one sample group; compare time windows or clusters instead")
            side_a, side_b = self._side(a, sa), self._side(b, sb)
            label, on = f"{tool}: {sa} vs {sb}", "time"
        else:
            raise ValueError(f"unknown comparison '{between}'; choose from subjects, windows, clusters")
        if span(side_a)[1] <= span(side_a)[0] or span(side_b)[1] <= span(side_b)[0]:
            raise ValueError("each side of a comparison needs a start before its end")

        res = {c: rel(c, side_a, c, side_b, on) for c in order}
        groups = [{"label": label, "clusters": ranked(res)[: top_n or len(res)]}]
        self._set(groups)
        # a cluster that moves on one side only has no second shape to compare
        one_sided = [c for c, r in res.items() if r["flat"][0] != r["flat"][1]]
        return {"tool": tool, "between": between, "metric": self._compare_metric(tool, th),
                "time_range": {"a": span(side_a), "b": span(side_b)}, "groups": groups,
                "flat_on_one_side": one_sided,
                "value_per_cluster": {c: brief(r) for c, r in res.items()}}

    @staticmethod
    def _compare_metric(tool, th):
        base = ("each cluster mean curve is replaced by the simple function that fits it best "
                f"(line, U / n, L / J, peak / valley, step; R2 >= {th.fit_r2})")
        return {
            "opposite": f"{base}; opposite when the Pearson r of the two fitted functions <= -{th.compare_r}, "
                        "or one only rises while the other only falls; neither may be flat",
            "similar": f"{base}; similar when the Pearson r of the two fitted functions >= {th.compare_r}, "
                       "or both are flat",
            "shifted": f"{base}; shifted when r reaches {th.compare_r} only after sliding one function in time",
            "diverging": f"{base}; diverging when the gap between the two functions grows steadily "
                         f"(Spearman rho of the gap against time >= {th.trend_rho})",
            "converging": f"{base}; converging when the gap between the two functions shrinks steadily "
                          f"(Spearman rho of the gap against time <= -{th.trend_rho})",
        }[tool]

    def select_by_similarity(self, subjects=None, match=None, top_n=None):
        """Pick the clusters whose ribbons follow the same curve as the cluster(s) picked so far.

        subjects  sample groups the curves are read in; default: the one the filters kept, else all
        match     all (similar in every sample group read) | any (in at least one). Needed when
                  several sample groups are read: MissingInput is raised when it is left out.
        """
        base = [c for c in self.targets if c in self.ds.clusters]
        if not base or len(base) >= len(self.ds.clusters):
            raise ValueError("similarity needs the cluster to compare with: pick it first")
        names = [s for s in (subjects or []) if s in self.ds.subjects] or None
        out = similar_clusters(self._ribbons(self.df, subjects=names), base, names, match, top_n)
        where = " and ".join(out["subjects"]) if out["match"] == "all" else " or ".join(out["subjects"])
        pairs = out["value_per_cluster"]
        why = "; ".join(
            f"{c} (" + ", ".join(f"{s}: {pairs[c][s]['note']}" for s in out["subjects"]
                                 if pairs[c][s]["similar"]) + ")" for c in out["clusters"])
        label = f"similar to {', '.join(base)} in {where}"
        groups = [{"label": label, "clusters": out["clusters"], "why": f"{label}: {why}"}]
        if not out["clusters"] and out["match"] == "all" and len(out["subjects"]) > 1:
            # nothing agrees in every sample group: show where the curves do agree, one sample
            # group at a time, so the answer is "none in all, but ..." and not an empty view
            out["none_in_all"] = True
            for s in out["subjects"]:
                hits = out["similar_per_subject"][s]
                label = f"similar to {', '.join(base)} in {s} only"
                groups.append({"label": label, "clusters": hits, "why": f"{label}: " + "; ".join(
                    f"{c} ({pairs[c][s]['note']})" for c in hits)})
        self._set(groups)
        out["groups"] = self.groups
        return out

    def describe_pattern(self):
        """Pattern of each target cluster per sample group, as the ribbon plot shows it.

        Detected without an LLM by detect/: trend, peaks, fitted function, ribbon
        width, constant features and absent timepoints, with a ready-made text.
        """
        base = self.ds.features
        if self.level2:
            base = base[base[self.cfg.level2].isin(self.level2)]

        def part(df):
            return {cl: {s: r.describe() for s, r in by.items()}
                    for cl, by in self._ribbons(self._target_rows(df)).items()}

        out = {"cluster": part(base)}
        if len(self.df) != len(base):
            out["filtered_features_only"] = part(self.df)
        return out


def _slice(side, ds):
    """One side of a comparison as the LLM wrote it, with the sample group matched to the data."""
    side = {k: v for k, v in (side or {}).items() if v not in (None, "")}
    if "subject" in side:
        side["subject"] = match(side["subject"], ds.subjects) or side["subject"]
    return side or None


def select(st, do, ctx):
    ds, s = ctx.ds, ctx.s
    if st["kind"] == "ribbon":
        do("evaluate ribbon and select cluster", "select_by_ribbon",
           criterion=st.get("criterion"), measure=st.get("measure"),
           subject=match(st.get("subject") or "", ds.subjects), top_n=st.get("top_n"))
        return
    a = _slice(st.get("a"), ds) or {}
    nothing_picked = not s.targets or len(s.targets) == len(ds.clusters)
    if (st.get("criterion") == "compare" and st.get("tool") == "similar" and st.get("between") == "clusters"
            and nothing_picked and ctx.filtered):
        # "the common patterns of X" planned as "which clusters look alike": with no cluster to
        # compare with, every pair of clusters would be compared and shown. Under a filter the
        # patterns that are common for X are those of the clusters that hold most of X.
        do("evaluate feature number and select cluster", "select_by_feature_number")
        ctx.assume('"Common patterns" was read as the patterns of the clusters that hold most of the '
                   "filtered features, not as clusters whose curves look alike; ask which clusters have "
                   "a similar shape to a named cluster for that.")
        ctx.want_pattern = True     # the question is about their patterns, whatever the descriptor says
        return
    if (st.get("criterion") == "compare" and st.get("tool") == "similar"
            and st.get("between") == "clusters" and 0 < len(s.targets) < len(ds.clusters)):
        # "similar to the cluster picked before": read on the ribbons (ribbon.py)
        do("compare ribbons and select similar cluster", "select_by_similarity",
           subjects=[a["subject"]] if a.get("subject") in ds.subjects else None,
           match=st.get("match"), top_n=st.get("top_n"))
    elif st.get("criterion") == "compare":
        do("compare patterns and select cluster", "select_by_comparison",
           tool=st["tool"], between=st.get("between") or "subjects",
           a=_slice(st.get("a"), ds), b=_slice(st.get("b"), ds), top_n=st.get("top_n"))
    else:
        tp = st.get("timepoint") if st.get("timepoint") in ds.timepoints else None
        do("evaluate pattern and select cluster", "select_by_pattern",
           criterion=st.get("criterion"), subject=match(st.get("subject") or "", ds.subjects),
           timepoint=tp, position=st.get("position"), top_n=st.get("top_n"))


def usable(st):
    """A comparison that does not say which relation it looks for is not a rule: guessing one
    (it used to be "opposite") picks clusters nobody asked for."""
    return st.get("criterion") != "compare" or bool(st.get("tool"))


def describe(d, do, ctx):
    if d.get("pattern") or getattr(ctx, "want_pattern", False):
        do("evaluate pattern", "describe_pattern")


def context(ds, dash_state):
    subjects = "; ".join(f"{s}: {', '.join(cols)}" for s, cols in ds.subjects.items())
    return [f"Sample groups and timepoint columns, in time order: {subjects}. Time words of a question "
            "(week, day, time point) map to the columns by position (first = early, last = late)."]
