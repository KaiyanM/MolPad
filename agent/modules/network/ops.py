"""Data operations of the network: edges above the importance score."""

import numpy as np


class Ops:
    """Edges, neighbours, components."""

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
            # the clusters were picked before; the question is whether they are linked. They are
            # one answer, so they stay one group and are shown together.
            base = list(self.targets)
            within = sorted(({"from": a, "to": b, "weight": adj[a][b]} for a in base for b in adj[a]
                             if b in base and key(a) < key(b)), key=lambda e: -e["weight"])
            if len(base) < 2:
                label = ("connected to " + ", ".join(sorted(adj[base[0]], key=key))) if base and adj[base[0]] else "isolated"
            elif not within:
                label = "no link among them"
            else:
                label = "linked to one another" if self.joined(base) else "partly linked to one another"
            groups = [{"label": label, "clusters": base}]
            out["neighbours"] = {c: adj[c] for c in base}
            out["within"] = within
        elif criterion == "components":
            comps = self._components(adj)
            out.update(n_components=len(comps), components=comps)
            return out
        else:
            raise ValueError(f"unknown network criterion '{criterion}'")
        if criterion in ("most_edges", "isolated", "neighbours"):
            # found through the graph structure: the playback shows these one by one.
            # An edge (strongest_edge, connected_pairs) keeps its two ends together, and so do
            # clusters that were picked before and are only checked for links (connectivity).
            groups = [{**g, "via": "network"} for g in groups]
        self._set(groups)
        out["groups"] = groups
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


def _threshold(text):
    if text in (None, "", "current"):
        return None
    try:
        return float(text)
    except ValueError:
        return str(text).lower()


def select(st, do, ctx):
    thr = _threshold(st.get("threshold"))
    s, f = ctx.s, ctx.f
    if st.get("criterion") in ("connectivity", "neighbours") and (not s.targets or len(s.targets) == len(ctx.ds.clusters)):
        # "are the X clusters connected?" with no step that picked clusters: every cluster would
        # be checked and shown. With a filter on, "the X clusters" are those that hold most of the
        # X features; without one the question is about the whole network, read as components.
        if ctx.filtered:
            do("evaluate feature number and select cluster", "select_by_feature_number")
            ctx.assume("The question does not say which clusters are meant. They were read as the clusters "
                       "that hold most of the filtered features; name clusters to check others.")
        else:
            s.targets, s.groups = [], []
            do("evaluate weight", "describe_weight", mode="components")
            return
    do("evaluate importance score and select cluster" if thr is not None
       else "evaluate weight and select cluster",
       "select_by_network", criterion=st.get("criterion"), threshold=thr)


def describe(d, do, ctx):
    if d.get("weight"):
        do("evaluate weight", "describe_weight", mode=d["weight"])


def context(ds, dash_state):
    return [f"An edge is drawn when weight > Importance Score. Now {dash_state['min_weight']} "
            f"(min {ds.slider_min}, max {ds.slider_max})."]
