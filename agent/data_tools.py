"""Backend data actions, run on the CSVs that feed the D3 dashboard.

The functions mirror what the dashboard computes so that a printed message
matches what the user sees:

- features without an annotation row are left out (state.js selectedFeatures);
- an edge is visible when weight > threshold (network.js);
- the default threshold is the median of |weight| rounded to 0.1 and the
  slider maximum is the 75th percentile (R/d3_payload.R).
"""

import re
from dataclasses import replace

import numpy as np
import pandas as pd

from . import patterns
from .config import CONFIG, LevelConfig

TREND_RHO = patterns.Thresholds().trend_rho   # |Spearman rho| at or above this is a steady trend
COVER_SHARE = 0.5    # "most of its features": smallest set of clusters covering this share
DEFAULT_TOP = 3      # candidates shown for a vague criterion


def _py(x):
    """Make numpy / pandas values JSON-serialisable."""
    if isinstance(x, dict):
        return {str(k): _py(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_py(v) for v in x]
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return None if np.isnan(x) else round(float(x), 3)
    return x


class Dataset:
    """The dashboard inputs, loaded once.

    Two sources, the same result:
        Dataset.from_payload(payload, cfg)  the JSON that gDashboard_d3() embeds in the page
        Dataset.from_csv(cfg)               the CSV copy named in config.py (tests, eval_trace)
    """

    def __init__(self, cfg, features, edges, timepoints, subjects, times, slider=None, clusters=()):
        """features: one row per feature with the id, "cluster", the colour column, one column per
        timepoint and the annotation columns. edges: from, to, weight. subjects: {name: [columns]}.
        times: {column: numeric time}. slider: {"min", "max", "value"}, else computed as the page does.
        clusters: nodes to show even without features or weighted edges (the page's own list)."""
        self.cfg = cfg
        self.features = features
        self.edges = edges[["from", "to", "weight"]].reset_index(drop=True)
        self.timepoints = list(timepoints)
        self.subjects = {k: list(v) for k, v in subjects.items()}
        self.times = dict(times)

        names = (set(self.features["cluster"]) | set(self.edges["from"]) | set(self.edges["to"])
                 | {str(c) for c in clusters})
        self.clusters = sorted(names, key=self.cluster_number)
        self.level1_values = sorted(self.features[cfg.level1].dropna().unique())
        self.level2_values = sorted(self.features[cfg.level2].dropna().unique())
        self.level2_by_level1 = {
            k: sorted(v.dropna().unique()) for k, v in self.features.groupby(cfg.level1)[cfg.level2]
        }

        absw = self.edges["weight"].abs()
        slider = slider or {}
        self.default_threshold = float(slider.get("value", round(float(absw.median()), 1)))
        self.slider_min = float(slider.get("min", 0.0))
        self.slider_max = float(slider.get("max", round(float(absw.quantile(0.75)), 1)))

    # ---- loaders ---------------------------------------------------------

    @classmethod
    def from_csv(cls, cfg: LevelConfig = CONFIG):
        d = cfg.data_dir
        data = pd.read_csv(d / cfg.data_file, index_col=0)
        labels = pd.read_csv(d / cfg.labels_file)
        ann = pd.read_csv(d / cfg.annotation_file, index_col=0)
        net = pd.read_csv(d / cfg.network_file, index_col=0)

        timepoints = [c for c in data.columns if c not in (cfg.id_col, cfg.color)]
        subjects = {}
        for c in timepoints:
            subjects.setdefault(c.split(cfg.subject_sep)[0], []).append(c)
        data["cluster"] = cfg.cluster_prefix + labels.iloc[:, 0].astype(str).values
        features = data.merge(ann, on=cfg.id_col, how="inner")
        edges = pd.DataFrame({"from": net["from"], "to": net["var_names"], "weight": net["weight"]})
        return cls(cfg, features, edges, timepoints, subjects, _times(timepoints))

    @classmethod
    def from_payload(cls, payload: dict, cfg: LevelConfig = None):
        """Build from the dashboard JSON (inst/d3dashboard/SCHEMA.md).

        Level 1 is Pathway, level 2 taxonomic.scope and the colour column type, as the page fixes
        them. Level 3 is the id plus the columns that have id links. Features without a
        taxonomic scope are left out, as the page does (state.js selectedFeatures).
        """
        cfg = cfg or LevelConfig()
        timepoints = [str(t) for t in payload["timepoints"]]
        rows = []
        for f in payload["features"]:
            r = {k: v for k, v in f.items() if k != "values"}
            r.update(zip(timepoints, f["values"]))
            rows.append(r)
        features = pd.DataFrame(rows)
        for c in timepoints:
            features[c] = pd.to_numeric(features[c], errors="coerce")
        features = features[features[cfg.level2].notna()].reset_index(drop=True)

        edges = pd.DataFrame(payload.get("edges") or [], columns=["from", "to", "weight"])
        edges["weight"] = pd.to_numeric(edges["weight"], errors="coerce")
        edges = edges[edges["weight"].notna()]

        subjects, times = {}, {}
        for s in payload.get("subjects") or []:
            subjects[str(s["name"])] = [str(c) for c in s["columns"]]
            for c, label in zip(s["columns"], s.get("labels") or []):
                t = _number(label)
                if t is not None:
                    times[str(c)] = t
        if not subjects:
            subjects = {"all": list(timepoints)}
        for c, t in _times(timepoints).items():
            times.setdefault(c, t)

        links = payload.get("id_links") or {}
        notes = {"GO": "GO term ids such as GO:0005524", "KEGG": "KEGG ortholog ids such as K03196"}
        level3 = (cfg.id_col,) + tuple(c for c in links if c in features.columns)
        cfg = replace(cfg, level3=level3,
                      level3_notes=("feature id",) + tuple(notes.get(links[c].get("type"), "database ids")
                                                           for c in level3[1:]),
                      cluster_prefix=_prefix(payload.get("clusters") or features["cluster"].unique()))
        return cls(cfg, features, edges, timepoints, subjects, times, payload.get("weight_slider"),
                   payload.get("clusters") or ())

    # ---- helpers ---------------------------------------------------------

    def cluster_number(self, name):
        m = re.search(r"(\d+)$", str(name))
        return int(m.group(1)) if m else 0

    def cluster_name(self, text):
        """'3', 'cluster_3', 'group 3' -> 'Group_3'; None when it is not a cluster."""
        if str(text) in self.clusters:
            return str(text)
        m = re.search(r"(\d+)\s*$", str(text))
        name = f"{self.cfg.cluster_prefix}{m.group(1)}" if m else None
        return name if name in self.clusters else None

    def axis(self, cols):
        """Time axis of some timepoint columns, with their numeric times."""
        return patterns.TimeAxis.of(cols, [self.times[c] for c in cols]
                                    if all(c in self.times for c in cols) else None)

    def time_of(self, col):
        return self.times.get(col, _number(col))

    def default_state(self):
        """Dashboard state at page load (inst/d3dashboard/js/state.js)."""
        first = self.features[self.cfg.level1].dropna().unique()
        return {
            "pathway": first[0] if len(first) else "",
            "min_weight": self.default_threshold,
            "selected_clusters": list(self.clusters),
            "layout": "force",
        }

    def time_position(self, col):
        """0..1 position of a timepoint inside its sample group."""
        cols = next(c for c in self.subjects.values() if col in c)
        t = [self.time_of(c) for c in cols]
        span = (max(t) - min(t)) or 1.0
        return (self.time_of(col) - min(t)) / span


def _number(label):
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*$", str(label))
    return float(m.group(1)) if m else None


def _times(cols):
    """Numeric time of each column from its trailing number; positions when that fails."""
    t = {c: _number(c) for c in cols}
    return t if all(v is not None for v in t.values()) else {c: float(i) for i, c in enumerate(cols)}


def _prefix(clusters):
    """Common text before the number of the cluster names: 'Group_3' -> 'Group_'."""
    heads = {re.sub(r"\d+$", "", str(c)) for c in clusters}
    return heads.pop() if len(heads) == 1 else ""


_ACTIVE = None


def use_dataset(ds: Dataset) -> Dataset:
    """Make `ds` the dataset every node and data action works on."""
    global _ACTIVE
    _ACTIVE = ds
    return ds


def load_dataset() -> Dataset:
    """The active dataset; the CSVs of config.py until use_dataset() sets another."""
    global _ACTIVE
    if _ACTIVE is None:
        _ACTIVE = Dataset.from_csv()
    return _ACTIVE


class Session:
    """Working state of one backend pass: the filtered features and the target clusters."""

    OPS = (
        "filter_cols", "filter_level1", "filter_level2", "filter_level3",
        "select_by_pattern", "select_by_ribbon", "select_by_comparison", "select_by_feature_number", "select_by_network",
        "select_by_feature_lookup", "select_given", "select_all", "select_examples",
        "describe_pattern", "describe_level2", "describe_level3", "describe_weight",
        "describe_feature_number",
    )

    def __init__(self, ds: Dataset, dash_state: dict | None = None):
        self.ds = ds
        self.cfg = ds.cfg
        state = dash_state or ds.default_state()
        self.df = ds.features
        self.cols = list(ds.timepoints)
        self.subject = None
        self.level1 = None
        self.level2 = []
        self.threshold = float(state["min_weight"])
        self.selected = list(state["selected_clusters"])
        self.targets = []      # clusters the answer is about
        self.groups = []       # [{"label", "clusters"}], set by the last selector

    def run(self, op: str, **args) -> dict:
        if op not in self.OPS:
            return {"error": f"unknown data action '{op}'"}
        try:
            return _py(getattr(self, op)(**args))
        except Exception as exc:  # a bad argument must not stop the graph
            return {"error": f"{type(exc).__name__}: {exc}"}

    # ---- helpers ---------------------------------------------------------

    def _set(self, groups):
        self.groups = [g for g in groups if g["clusters"]]
        seen = []
        for g in self.groups:
            seen += [c for c in g["clusters"] if c not in seen]
        self.targets = seen

    def _subjects(self, subject=None):
        names = [subject] if subject else ([self.subject] if self.subject else list(self.ds.subjects))
        return {s: [c for c in self.ds.subjects[s] if c in self.cols] for s in names}

    def _shape(self, values, cols):
        """Trend, peak and a one-word shape for one mean curve (agent/patterns)."""
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

    def _counts(self, df=None):
        df = self.df if df is None else df
        return df.groupby("cluster").size().reindex(self.ds.clusters, fill_value=0).sort_values(
            ascending=False, kind="stable")

    def _adjacency(self, threshold=None):
        thr = self.threshold if threshold is None else threshold
        adj = {c: {} for c in self.ds.clusters}
        for e in self.ds.edges.itertuples():
            if e.weight > thr and e._1 != e.to:
                w = max(e.weight, adj[e._1].get(e.to, -np.inf))
                adj[e._1][e.to] = w
                adj[e.to][e._1] = w
        return adj

    def _components(self, adj):
        seen, comps = set(), []
        for c in self.ds.clusters:
            if c in seen:
                continue
            comp, stack = [], [c]
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                comp.append(n)
                stack += list(adj[n])
            comps.append(sorted(comp, key=self.ds.cluster_number))
        return comps

    def joined(self, clusters):
        """True when the clusters form one connected group at the current threshold."""
        if len(clusters) < 2:
            return False
        adj = self._adjacency()
        seen, stack = set(), [clusters[0]]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack += [m for m in adj[n] if m in clusters]
        return seen == set(clusters)

    # ---- filters ---------------------------------------------------------

    def filter_cols(self, subject):
        if subject not in self.ds.subjects:
            raise ValueError(f"no sample group '{subject}'; choose from {list(self.ds.subjects)}")
        self.subject = subject
        self.cols = list(self.ds.subjects[subject])
        return {"columns": self.cols}

    def filter_level1(self, value):
        if value not in self.ds.level1_values:
            raise ValueError(f"'{value}' is not a {self.cfg.level1} value")
        self.level1 = value
        self.df = self.df[self.df[self.cfg.level1] == value]
        return {"n_features": len(self.df)}

    def filter_level2(self, values):
        bad = [v for v in values if v not in self.ds.level2_values]
        if bad:
            raise ValueError(f"{bad} not in {self.cfg.level2}")
        self.level2 = list(values)
        self.df = self.df[self.df[self.cfg.level2].isin(values)]
        return {"n_features": len(self.df)}

    def filter_level3(self, column, values=None, has_annotation=False):
        if column not in self.cfg.level3:
            raise ValueError(f"'{column}' is not a level-3 column {self.cfg.level3}")
        col = self.df[column].astype(str)
        if not values:
            self.df = self.df[col != self.cfg.missing]
            return {"n_features": len(self.df), "kept": f"rows with a {column}"}
        ids = [str(v).split(":", 1)[1] if str(v).lower().startswith("ko:") else str(v) for v in values]
        found = {}
        for i in ids:
            found[i] = int(col.str.contains(rf"(?:^|,)\s*(?:ko:)?{re.escape(i)}\s*(?:,|$)").sum())
        pat = "|".join(re.escape(i) for i in ids)
        self.df = self.df[col.str.contains(rf"(?:^|,)\s*(?:ko:)?(?:{pat})\s*(?:,|$)")]
        return {"n_features": len(self.df), "features_per_id": found}

    # ---- selectors -------------------------------------------------------

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
                return {"early": pos <= 0.25, "mid": 0.25 < pos < 0.75, "late": pos >= 0.75}[position or "mid"]
            # an even curve has no peak worth the name
            picked = [c for c in order
                      if any(s["shape"] != "even" and hit(s["peak"]) for s in curves[c].values())]
            groups = [{"label": f"peak at {timepoint or position or 'mid'}", "clusters": picked}]
            metric = "timepoint of the maximum of the cluster mean, per sample group"
        elif criterion == "color_divergence":
            lines = self.df.groupby(["cluster", self.cfg.color])[self.cols].mean()
            gap = (lines.groupby("cluster").max() - lines.groupby("cluster").min()).mean(axis=1)
            ranked = gap.sort_values(ascending=False)
            groups = [{"label": f"{criterion} #{i + 1}", "clusters": [c]}
                      for i, c in enumerate(ranked.index[: top_n or DEFAULT_TOP])]
            self._set(groups)
            return {"metric": "mean gap between the highest and lowest colour mean line",
                    "groups": groups, "value_per_cluster": ranked.round(3).to_dict()}
        else:
            raise ValueError(f"unknown pattern criterion '{criterion}'")

        if top_n:
            groups = [{**g, "clusters": g["clusters"][:top_n]} for g in groups]
        self._set(groups)
        shapes = {c: {s: {"shape": v["shape"], "peak": v["peak"]} for s, v in curves[c].items()} for c in order}
        return {"metric": metric, "groups": groups, "shape_per_cluster": shapes}

    def select_by_ribbon(self, criterion, measure=None, subject=None, top_n=None):
        """Pick clusters by their ribbon in the pattern plot (agent/patterns/ribbon).

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
        """Pick clusters by how two of their mean curves relate (agent/patterns/compare).

        Each curve is first replaced by the function fitted to it (agent/patterns/fit), over all
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

    def select_by_feature_number(self, top_n=None):
        counts = self._counts()
        total = int(counts.sum())
        if total == 0:
            self._set([])
            return {"total": 0, "clusters": []}
        if top_n:
            picked = list(counts.index[:top_n])
            rule = f"top {top_n} by feature count"
        else:
            share = counts.cumsum() / total
            picked = list(counts.index[: int((share < COVER_SHARE).sum()) + 1])
            rule = f"smallest set of clusters holding at least {int(COVER_SHARE * 100)}% of the features"
        self._set([{"label": None, "clusters": picked}])
        return {"rule": rule, "clusters": picked, "total": total,
                "features_per_cluster": counts.to_dict(),
                "share_of_selected": float(counts[picked].sum() / total)}

    def select_by_network(self, criterion, threshold=None):
        if threshold is not None:
            named = {"current": self.threshold, "default": self.ds.default_threshold,
                     "max": self.ds.slider_max, "min": self.ds.slider_min}
            self.threshold = float(named.get(threshold, threshold))
        adj = self._adjacency()
        out = {"threshold": self.threshold}
        key = self.ds.cluster_number

        if criterion == "most_edges":
            degree = {c: len(adj[c]) for c in self.ds.clusters}
            best = max(degree.values())
            groups = [{"label": "most edges", "clusters": [c for c in degree if degree[c] == best]}]
            out["edges_per_cluster"] = degree
        elif criterion == "strongest_edge":
            e = self.ds.edges.loc[self.ds.edges["weight"].idxmax()]
            groups = [{"label": "strongest edge", "clusters": sorted([e["from"], e["to"]], key=key)}]
            out["edge"] = {"from": e["from"], "to": e["to"], "weight": e["weight"]}
        elif criterion == "isolated":
            groups = [{"label": "isolated", "clusters": [c]} for c in self.ds.clusters if not adj[c]]
        elif criterion == "connected_pairs":
            pairs = sorted({tuple(sorted((a, b), key=key)) for a in adj for b in adj[a]},
                           key=lambda p: -adj[p[0]][p[1]])
            groups = [{"label": f"weight {adj[a][b]:.2f}", "clusters": [a, b]} for a, b in pairs]
        elif criterion == "neighbours":
            base = list(self.targets)
            near = sorted({n for c in base for n in adj[c]} - set(base), key=key)
            groups = [{"label": "cluster and its neighbours", "clusters": base + near}]
            out["neighbours"] = {c: adj[c] for c in base}
        elif criterion == "connectivity":
            groups = [{"label": ("connected to " + ", ".join(sorted(adj[c], key=key))) if adj[c] else "isolated",
                       "clusters": [c]} for c in self.targets]
            out["neighbours"] = {c: adj[c] for c in self.targets}
        elif criterion == "components":
            comps = self._components(adj)
            out.update(n_components=len(comps), components=comps)
            return out
        else:
            raise ValueError(f"unknown network criterion '{criterion}'")
        self._set(groups)
        out["groups"] = groups
        return out

    def select_by_feature_lookup(self, top_n=None):
        counts = self._counts()
        counts = counts[counts > 0]
        picked = list(counts.index[: top_n or len(counts)])
        self._set([{"label": None, "clusters": picked}])
        cols = [self.cfg.id_col, "cluster", self.cfg.level1, self.cfg.level2]
        return {"n_features": len(self.df), "features_per_cluster": counts.to_dict(),
                "clusters": picked, "first_rows": self.df[cols].head(20).to_dict("records")}

    def select_given(self, clusters=None):
        names = [self.ds.cluster_name(c) for c in (clusters or [])]
        picked = [n for n in names if n] or list(self.selected)
        self._set([{"label": None, "clusters": picked}])
        return {"clusters": picked}

    def select_all(self):
        self.targets, self.groups = list(self.ds.clusters), []
        return {"clusters": "all"}

    def select_examples(self, by="level2_composition", values=None, top_n=None):
        """Example clusters for what the question names (agent/examples.py)."""
        from .examples import EXAMPLE_FINDERS

        if by not in EXAMPLE_FINDERS:
            raise ValueError(f"no example finder '{by}'; choose from {list(EXAMPLE_FINDERS)}")
        out = EXAMPLE_FINDERS[by](self, values=values, top_n=top_n)
        self._set(out["groups"])
        return out

    # ---- descriptors -----------------------------------------------------

    def _target_rows(self, df):
        return df[df["cluster"].isin(self.targets or self.ds.clusters)]

    def describe_pattern(self):
        """Pattern of each target cluster per sample group, as the ribbon plot shows it.

        Detected without an LLM by agent/patterns: trend, peaks, fitted function, ribbon
        width, constant features and absent timepoints, with a ready-made text.
        """
        base = self.ds.features
        if self.level2:
            base = base[base[self.cfg.level2].isin(self.level2)]
        all_times = sorted({self.ds.time_of(c) for c in self.ds.timepoints})

        def part(df):
            out = {}
            for cl, g in self._target_rows(df).groupby("cluster"):
                out[cl] = {}
                for subject, cols in self._subjects().items():
                    d = patterns.describe(g[cols].values, cols, times=self.ds.axis(cols).times,
                                          groups=g[self.cfg.color].values,
                                          expected_times=all_times)
                    out[cl][subject] = {
                        "shape": d["shape"],
                        "peak": None if d["shape"] == "even" else d["peaks"]["highest"]["at"],
                        "n_peaks": d["peaks"]["n_peaks"],
                        "fitted_shape": d["fit"]["shape"],      # the simple function that fits the mean
                        "fit_r2": d["fit"]["r2"],
                        "mean": [round(v, 2) for v in d["mean"].values()],
                        "ribbon_width": d["spread"]["ribbon_width"]["mean"],
                        "ribbon_max_width": (d["ribbon"] or {}).get("width", {}).get("max"),
                        "ribbon_area": (d["ribbon"] or {}).get("width", {}).get("area"),
                        "ribbon_trend": (d["ribbon"] or {}).get("trend", {}).get("direction"),
                        "fraction_constant_features": d["missingness"]["fraction_constant"],
                        "text": d["text"],
                    }
            return out

        out = {"cluster": part(base)}
        if len(self.df) != len(base):
            out["filtered_features_only"] = part(self.df)
        return out

    def describe_level2(self):
        rows = self._target_rows(self.df)
        out = {}
        for cl, g in rows.groupby("cluster"):
            n = g[self.cfg.level2].value_counts()
            out[cl] = {"total": len(g), "counts": n.to_dict(), "fractions": (n / len(g)).round(3).to_dict()}
        if self.level2:   # shares are of the features the level-2 filter kept, not the whole cluster
            out = {cl: {**v, "within": list(self.level2)} for cl, v in out.items()}
        return out

    def describe_level3(self, column, mode="frequency"):
        if column not in self.cfg.level3:
            raise ValueError(f"'{column}' is not a level-3 column {self.cfg.level3}")
        rows = self._target_rows(self.df)
        out = {}
        for cl, g in rows.groupby("cluster"):
            col = g[column].astype(str)
            has = col != self.cfg.missing
            if mode == "coverage":
                out[cl] = {"with": int(has.sum()), "without": int((~has).sum()),
                           "fraction_without": float((~has).mean())}
            elif mode == "list":
                out[cl] = {"n": int(has.sum()), "first": col[has].head(20).tolist()}
            else:
                tokens = col[has].str.split(",").explode().str.strip().str.replace(r"^ko:", "", regex=True)
                out[cl] = {"n_annotated": int(has.sum()), "top": tokens.value_counts().head(5).to_dict()}
        return out

    def describe_weight(self, mode="neighbours"):
        adj = self._adjacency()
        if mode == "components":
            comps = self._components(adj)
            return {"threshold": self.threshold, "n_components": len(comps), "components": comps}
        clusters = self.targets or self.ds.clusters
        if mode == "degree":
            return {"threshold": self.threshold, "edges_per_cluster": {c: len(adj[c]) for c in clusters}}
        return {"threshold": self.threshold, "neighbours": {c: adj[c] for c in clusters}}

    def describe_feature_number(self):
        counts = self._counts()
        return {"features_per_cluster": counts.to_dict(), "largest": counts.index[0], "total": int(counts.sum())}
