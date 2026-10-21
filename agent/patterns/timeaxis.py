"""The time axis of a series: labels, numeric times, and gaps."""

import re
from dataclasses import dataclass

import numpy as np


def _number(label):
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*$", str(label))
    return float(m.group(1)) if m else None


@dataclass(frozen=True)
class TimeAxis:
    labels: tuple
    times: tuple

    @classmethod
    def of(cls, labels, times=None):
        """Times default to the number at the end of each label (A_3 -> 3), else 0, 1, 2, ..."""
        labels = tuple(str(x) for x in labels)
        if times is None:
            parsed = [_number(x) for x in labels]
            ok = all(p is not None for p in parsed) and len(set(parsed)) == len(parsed)
            times = parsed if ok else range(len(labels))
        times = tuple(float(t) for t in times)
        if len(times) != len(labels):
            raise ValueError("labels and times differ in length")
        return cls(labels, times)

    def __len__(self):
        return len(self.labels)

    def position(self, i):
        """0..1 position of timepoint i within the time range."""
        span = (max(self.times) - min(self.times)) or 1.0
        return (self.times[i] - min(self.times)) / span

    def phase(self, i, th):
        p = self.position(i)
        return "early" if p <= th.early else "late" if p >= th.late else "mid"

    def gaps(self, expected=None):
        """Timepoints that are absent from the axis.

        `expected` is the full list of times (for example those of another
        sample group). Without it, the axis is checked against a regular grid
        with its own smallest step.
        """
        have = sorted(self.times)
        if expected is None:
            steps = np.diff(have)
            if len(steps) == 0 or steps.min() <= 0:
                return []
            step = steps.min()
            expected = np.arange(have[0], have[-1] + step / 2, step)
        return [float(t) for t in expected if not any(abs(t - h) < 1e-9 for h in have)]
