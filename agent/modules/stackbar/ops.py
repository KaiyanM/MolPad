"""Data operations of the stacked bar plot: the level-2 mix of a cluster."""

from .examples import EXAMPLE_FINDERS


class Ops:
    """Level-2 composition."""

    def select_examples(self, by="level2_composition", values=None, top_n=None):
        """Example clusters for what the question names (examples.py)."""
        if by not in EXAMPLE_FINDERS:
            raise ValueError(f"no example finder '{by}'; choose from {list(EXAMPLE_FINDERS)}")
        out = EXAMPLE_FINDERS[by](self, values=values, top_n=top_n)
        self._set(out["groups"])
        return out

    def describe_level2(self, classes=None):
        """Level-2 counts of each target cluster, as the stacked bar shows them.

        `classes`: the level-2 values set against each other (a level-2 contrast). They are
        counted together even while the filter keeps one of them, so a run that keeps only
        Bacilli still reports how many Clostridia the cluster holds. Without `classes`, the
        rows the filters kept are counted; `kept` names the level-2 filter when one is set.
        """
        if classes:
            df = self.ds.features
            if self.level1:
                df = df[df[self.cfg.level1] == self.level1]
            df = df[df[self.cfg.level2].isin(classes)]
        else:
            df = self.df
        totals = self.ds.features.groupby("cluster").size()
        out = {}
        for cl, g in self._target_rows(df).groupby("cluster"):
            n = g[self.cfg.level2].value_counts()
            out[cl] = {"total": len(g), "counts": {k: int(v) for k, v in n.items()},
                       "cluster_total": int(totals.get(cl, 0))}
            if classes:
                out[cl]["classes"] = list(classes)
                out[cl]["counts"] = {c: out[cl]["counts"].get(c, 0) for c in classes}
            elif self.level2:
                out[cl]["kept"] = list(self.level2)
        return out


def select(st, do, ctx):
    by = st.get("example_by") or "level2_composition"
    do(f"infer example clusters by {by.replace('_', ' ').replace('level2', 'level-2')}",
       "select_examples", by=by, top_n=st.get("top_n"))


def describe(d, do, ctx):
    # The class mix is read as the bar shows it. In a level-2 contrast every compared class is
    # counted, although this run keeps one, so the counts of the classes can be set side by side.
    # With one class kept and no contrast the mix is that class alone, a filter artifact: skip it.
    # With several classes kept, always read it, so a message never names a class for a cluster
    # without a finding behind it.
    if ctx.contrast_l2:
        do("evaluate level2 (" + " and ".join(ctx.f["level2"]) + ")", "describe_level2", classes=ctx.f["level2"])
    elif len(ctx.level2) > 1 or (d.get("level2") and len(ctx.level2) != 1):
        do("evaluate level2", "describe_level2")
