"""Data operations on the clusters themselves: their size, and the ones a question names."""

from ...core.dataset import COVER_SHARE


class Ops:
    """Size and named clusters."""

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

    def select_given(self, clusters=None):
        names = [self.ds.cluster_name(c) for c in (clusters or [])]
        picked = [n for n in names if n] or list(self.selected)
        self._set([{"label": None, "clusters": picked}])
        return {"clusters": picked}

    def select_all(self):
        self.targets, self.groups = list(self.ds.clusters), []
        return {"clusters": "all"}

    def describe_feature_number(self):
        counts = self._counts()
        return {"features_per_cluster": counts.to_dict(), "largest": counts.index[0], "total": int(counts.sum())}


def select(st, do, ctx):
    if st["kind"] == "feature_number":
        do("evaluate feature number and select cluster", "select_by_feature_number", top_n=st.get("top_n"))
    elif st["kind"] == "given":
        do("select current cluster" if not st.get("clusters") else "select named cluster",
           "select_given", clusters=st.get("clusters"))
    else:
        do("read cluster data", "select_all")


def describe(d, do, ctx):
    counted = any(st["kind"] == "feature_number" for st in ctx.chosen)   # counts are already in its result
    if d.get("feature_number") and not counted:
        do("evaluate feature number", "describe_feature_number")


def context(ds, dash_state):
    return [f"Clusters {ds.clusters[0]} .. {ds.clusters[-1]}, one network node each."]
