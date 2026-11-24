"""Data operations of the feature table: look features up by their level-3 ids."""

import re

from ...core.session import match


class Ops:
    """Level 3: the ids of the features."""

    def _id_prefix(self, column):
        return self.ds.card["ids"].get(column, {}).get("prefix", "")

    def filter_level3(self, column, values=None, has_annotation=False):
        if column not in self.cfg.level3:
            raise ValueError(f"'{column}' is not a level-3 column {self.cfg.level3}")
        col = self.df[column].astype(str)
        if not values:
            self.df = self.df[col != self.cfg.missing]
            return {"n_features": len(self.df), "kept": f"rows with a {column}"}
        prefix = self._id_prefix(column)      # the ids may carry one in the data ("ko:K03196")
        ids = [str(v)[len(prefix):] if prefix and str(v).lower().startswith(prefix.lower()) else str(v)
               for v in values]
        lead = f"(?:{re.escape(prefix)})?" if prefix else ""
        found = {}
        for i in ids:
            found[i] = int(col.str.contains(rf"(?:^|,)\s*{lead}{re.escape(i)}\s*(?:,|$)").sum())
        pat = "|".join(re.escape(i) for i in ids)
        self.df = self.df[col.str.contains(rf"(?:^|,)\s*{lead}(?:{pat})\s*(?:,|$)")]
        return {"n_features": len(self.df), "features_per_id": found}

    def select_by_feature_lookup(self, top_n=None):
        counts = self._counts()
        counts = counts[counts > 0]
        picked = list(counts.index[: top_n or len(counts)])
        self._set([{"label": None, "clusters": picked}])
        cols = [self.cfg.id_col, "cluster", self.cfg.level1, self.cfg.level2]
        return {"n_features": len(self.df), "features_per_cluster": counts.to_dict(),
                "clusters": picked, "first_rows": self.df[cols].head(20).to_dict("records")}

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
                tokens = col[has].str.split(",").explode().str.strip().str.replace(
                    "^" + re.escape(self._id_prefix(column)), "", regex=True)
                out[cl] = {"n_annotated": int(has.sum()), "top": tokens.value_counts().head(5).to_dict()}
        return out


def select(st, do, ctx):
    do("evaluate features and select cluster", "select_by_feature_lookup", top_n=st.get("top_n"))


def describe(d, do, ctx):
    dcol = match(d.get("level3_column") or "", ctx.ds.cfg.level3)
    if dcol:
        res = do("evaluate level3", "describe_level3", column=dcol, mode=d.get("level3_mode") or "frequency")
        top = next((list(v["top"]) for v in res.values() if isinstance(v, dict) and v.get("top")), None)
        if top and not ctx.table:   # show the most common id in the table
            ctx.table = {"action": f"table search {top[0]}", "fn": "search table", "param": top[0]}


def context(ds, dash_state):
    return [f"Level 3 table columns: {', '.join(ds.cfg.level3)}"]
