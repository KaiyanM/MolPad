"""Example clusters: pick clusters that illustrate what the user asked about. No LLM.

A question such as "Do Flavobacteriia and Bacilli peak at different weeks?" names
things (here two classes) but no cluster. An example finder picks, for each named
thing, the cluster that shows it best, and says in one line why that cluster was
picked. The line is reused as the first sentence of the message under it.

One finder per kind of evidence, named examples_by_<evidence>:

    examples_by_level2_composition   the cluster whose features are mostly that class

More finders (for example by the ribbon plot) are added to EXAMPLE_FINDERS. Each
takes (session, values, top_n) and returns

    {"by", "values", "groups": [{"label", "clusters", "why"}], "details"}
"""

MIN_COVERAGE = 0.05   # a cluster must hold at least this share of the class's features ...
MIN_FEATURES = 20     # ... or at least this many of them


def _pct(x):
    return f"{100 * x:.1f}%" if 0 < x < 0.1 else f"{100 * x:.0f}%"


def examples_by_level2_composition(session, values=None, top_n=None):
    """For each level-2 value, the cluster(s) with the highest share of that value.

    Shares are of the whole cluster (the level-1 and level-2 filters are ignored), so
    "21% of its features" means 21% of everything the cluster holds.
    """
    ds, cfg = session.ds, session.cfg
    values = list(values or session.level2)
    if not values:
        raise ValueError(f"name at least one {cfg.level2_name} ({cfg.level2}) to find examples for")
    bad = [v for v in values if v not in ds.level2_values]
    if bad:
        raise ValueError(f"{bad} not in {cfg.level2}")

    base = ds.features
    totals = base.groupby("cluster").size()
    counts = base.groupby(["cluster", cfg.level2]).size()

    groups, details = [], {}
    for value in values:
        n_value = int((base[cfg.level2] == value).sum())
        rows = {}
        for cl in ds.clusters:
            n = int(counts.get((cl, value), 0))
            if n == 0:
                continue
            rows[cl] = {"n": n, "share": round(n / int(totals[cl]), 3),
                        "coverage": round(n / n_value, 3)}
        details[value] = rows
        ok = [c for c, r in rows.items() if r["coverage"] >= MIN_COVERAGE or r["n"] >= MIN_FEATURES]
        ok.sort(key=lambda c: (-rows[c]["share"], -rows[c]["n"]))
        for cl in ok[: top_n or 1]:
            r = rows[cl]
            why = (f"{_pct(r['share'])} of its features are {value}; it holds "
                   f"{_pct(r['coverage'])} of all {value} features")
            same = next((g for g in groups if g["clusters"] == [cl]), None)
            if same:   # one cluster is the best example for two values: show it once
                same["label"] += f" and {value}"
                same["why"] += f"; {why}"
            else:
                groups.append({"label": f"example of {value}", "clusters": [cl], "why": why})
    return {"by": "level2_composition", "values": values, "groups": groups, "details": details}


EXAMPLE_FINDERS = {
    "level2_composition": examples_by_level2_composition,
}
