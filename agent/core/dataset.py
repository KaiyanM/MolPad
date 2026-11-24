"""The data of one dashboard (Dataset), read from the CSVs or from the page.

The data operations of the modules (agent/modules/*/ops.py) mirror what the dashboard computes so that a printed message
matches what the user sees:

- features without an annotation row are left out (state.js selectedFeatures);
- an edge is visible when weight > threshold (network.js);
- the default threshold is the median of |weight| rounded to 0.1 and the
  slider maximum is the 75th percentile (R/d3_payload.R).
"""

import re
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from .config import LevelConfig
from . import datacard
from .timeaxis import TimeAxis, _number

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
        Dataset.from_csv(folder, ...)       the same tables as CSV files (tests/cheese.py)
    """

    def __init__(self, cfg, features, edges, timepoints, subjects, times, slider=None, clusters=(),
                 description=None, context=None, id_links=None):
        """features: one row per feature with the id, "cluster", the colour column, one column per
        timepoint and the annotation columns. edges: from, to, weight. subjects: {name: [columns]}.
        times: {column: numeric time}. slider: {"min", "max", "value"}, else computed as the page does.
        clusters: nodes to show even without features or weighted edges (the page's own list).
        description, context: what the data is in words (core/datacard.py); id_links: the id
        columns, {column: {"type", "pattern"}}; without it the level-3 columns of cfg."""
        if id_links is None:
            id_links = datacard.guess_links(c for c in cfg.level3 if c != cfg.id_col)
        self.card = datacard.build(features, cfg, description, context, id_links)
        cfg = replace(cfg, background=self.card["background"], missing=self.card["missing"],
                      level1_name=self.card["level1"]["name"], level2_name=self.card["level2"]["name"],
                      level3=(cfg.id_col,) + tuple(self.card["ids"]),
                      level3_notes=(f"{self.card['feature']['name']} id",)
                      + tuple(datacard.id_note(self.card, c) for c in self.card["ids"]))
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
    def from_csv(cls, folder, data, labels, annotation, network, ids=None, description=None,
                 cfg: LevelConfig = None):
        """Build from the tables of the R workflow saved as CSV files in `folder`.

        data: ID, the timepoint columns, the colour column. labels: one cluster number per row of
        data. annotation: ID plus the level columns. network: from, var_names (= to), weight.
        ids: {column: id type} of the id columns. description: the study, as in the page.
        """
        cfg = cfg or LevelConfig()
        d = Path(folder)
        data = pd.read_csv(d / data, index_col=0)
        labels = pd.read_csv(d / labels)
        ann = pd.read_csv(d / annotation, index_col=0)
        net = pd.read_csv(d / network, index_col=0)
        links = {c: ({"type": t, "pattern": datacard.ID_TYPES[t]["pattern"]} if t in datacard.ID_TYPES
                     else {"type": t}) for c, t in (ids or {}).items()}

        timepoints = [c for c in data.columns if c not in (cfg.id_col, cfg.color)]
        subjects = {}
        for c in timepoints:
            subjects.setdefault(c.split(cfg.subject_sep)[0], []).append(c)
        data["cluster"] = cfg.cluster_prefix + labels.iloc[:, 0].astype(str).values
        features = data.merge(ann, on=cfg.id_col, how="inner")
        edges = pd.DataFrame({"from": net["from"], "to": net["var_names"], "weight": net["weight"]})
        return cls(cfg, features, edges, timepoints, subjects, _times(timepoints),
                   description=description, id_links=links)

    @classmethod
    def from_payload(cls, payload: dict, cfg: LevelConfig = None, context: dict = None):
        """Build from the dashboard JSON (inst/d3dashboard/SCHEMA.md).

        Level 1 is Pathway, level 2 taxonomic.scope and the colour column type, as the page fixes
        them; what they stand for is in the page's `dataset` block, which `context` (the entries
        of a context file) overrules. Level 3 is the id plus the columns that have id links.
        Features without a taxonomic scope are left out.
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

        links = {c: v for c, v in (payload.get("id_links") or {}).items() if c in features.columns}
        cfg = replace(cfg, cluster_prefix=_prefix(payload.get("clusters") or features["cluster"].unique()))
        return cls(cfg, features, edges, timepoints, subjects, times, payload.get("weight_slider"),
                   payload.get("clusters") or (), description=payload.get("dataset"),
                   context=context, id_links=links)

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
        return TimeAxis.of(cols, [self.times[c] for c in cols]
                                    if all(c in self.times for c in cols) else None)

    def time_of(self, col):
        return self.times.get(col, _number(col))

    def default_state(self):
        """Dashboard state at page load (inst/d3dashboard/js/state.js): both filters on All."""
        return {
            "level1": [],                 # [] = all
            "level2": [],
            "scope": "filtered",          # what the views of the selected clusters show
            "colour_by": "level1",        # what the ribbon lines are grouped by
            "pathway": "",                # older name: the one level-1 value, "" for none / several
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
    """The active dataset, set with use_dataset(). The agent has no data of its own."""
    if _ACTIVE is None:
        raise RuntimeError("no dataset is loaded: start the agent with --dashboard <index.html>, "
                           "or call use_dataset(payload.load(page)) first")
    return _ACTIVE
