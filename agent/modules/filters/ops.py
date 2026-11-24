"""Data operations of the filter bar: keep the features of a level-1 / level-2 value, and read
the timepoint columns of one sample group."""

class Ops:
    """The shared filters."""

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
