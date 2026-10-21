"""Cut-offs used by the detectors, in one place so they can be tuned per dataset."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    # trend
    flat_range: float = 0.5        # a mean curve whose max - min is below this is "even" (data units)
    trend_rho: float = 0.8         # |Spearman rho| against time needed for increase / decrease
    # peaks
    peak_prominence: float = 0.25  # a peak must stand out by this share of the curve's range
    early: float = 0.25            # position in the time range at or before which a point is "early"
    late: float = 0.75             # ... at or after which it is "late"
    # missingness
    constant_tol: float = 1e-9     # a feature whose values differ by less than this is "constant"
    # spread
    consistent_r: float = 0.7      # mean feature-to-mean correlation at or above this is "consistent"
    # fit
    fit_r2: float = 0.8            # a fitted function must explain this share of the variance to count
    # compare
    compare_r: float = 0.7         # |r| of the two fitted functions needed for "similar" / "opposite"
    shift_gain: float = 0.2        # r must rise by this after sliding one curve for "shifted"


DEFAULT = Thresholds()
