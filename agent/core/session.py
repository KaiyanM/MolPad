"""The working state of one backend pass, and how a data operation is run on it.

The operations themselves are in the modules (agent/modules/<name>/ops.py, class Ops). The
Session the agent uses is this base plus the Ops of every module (agent/data_tools.py).
"""

from .dataset import Dataset, _py


class MissingInput(ValueError):
    """An operation needs an input the question did not give.

    field    the argument that is missing
    options  the values it can take
    default  the value assumed when nobody is asked
    say      one sentence for the user: what was assumed and how to ask for another reading
    """

    def __init__(self, field, options, default, what="", say=""):
        self.field, self.options, self.default, self.what = field, list(options), default, what
        self.say = say or f"{what or 'this step'} used {field} = {default}; other choices: " \
                          + ", ".join(str(o) for o in options if o != default)
        super().__init__(f"{what or 'this'} needs '{field}': choose from {', '.join(map(str, options))}")


def match(value, valid):
    """Case-insensitive match of an LLM-written value against the valid ones."""
    low = {str(v).lower(): v for v in valid}
    return low.get(str(value).strip().lower())


class SessionBase:
    """Working state of one backend pass: the filtered features and the target clusters."""

    OPS = ()   # names of the data operations; filled from the modules

    def __init__(self, ds: Dataset, dash_state: dict | None = None):
        self.ds = ds
        self.cfg = ds.cfg
        state = dash_state or ds.default_state()
        self.df = ds.features
        self.cols = list(ds.timepoints)
        self.subject = None
        self.level1 = None
        self.level2 = []
        self.colour_by = state.get("colour_by") or "level1"   # the page's 'Colour lines by'
        self.threshold = float(state["min_weight"])
        self.selected = list(state["selected_clusters"])
        self.targets = []      # clusters the answer is about
        self.groups = []       # [{"label", "clusters"}], set by the last selector

    def run(self, op: str, **args) -> dict:
        if op not in self.OPS:
            return {"error": f"unknown data action '{op}'"}
        try:
            return _py(getattr(self, op)(**args))
        except MissingInput:      # the caller decides: assume the default, or ask
            raise
        except Exception as exc:  # a bad argument must not stop the graph
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _set(self, groups):
        self.groups = [g for g in groups if g["clusters"]]
        seen = []
        for g in self.groups:
            seen += [c for c in g["clusters"] if c not in seen]
        self.targets = seen

    def _subjects(self, subject=None):
        names = [subject] if subject else ([self.subject] if self.subject else list(self.ds.subjects))
        return {s: [c for c in self.ds.subjects[s] if c in self.cols] for s in names}

    def _counts(self, df=None):
        df = self.df if df is None else df
        return df.groupby("cluster").size().reindex(self.ds.clusters, fill_value=0).sort_values(
            ascending=False, kind="stable")

    def _target_rows(self, df):
        return df[df["cluster"].isin(self.targets or self.ds.clusters)]
