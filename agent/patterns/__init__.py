"""Pattern detection for longitudinal data, without an LLM.

Each module describes one aspect of a group of features measured over time
(for example one cluster in one sample group):

    trend        increase / decrease / even / mixed, slope, net change
    peaks        where the peaks and troughs are, and how many
    changes      largest rise and fall between timepoints, turning points
    missingness  missing values per timepoint, constant features, gaps in the time axis
    spread       ribbon width and feature-to-feature variance, consistency with the mean
    divergence   how far the mean lines of sub-groups (colours) are apart
    describe     all of the above in one dict, plus a one-paragraph text

The ribbon around the mean curve (the curve itself is described above):

    width        width per timepoint, mean / max / min width, width variability, area
    width_trend  whether the ribbon expands, contracts or stays steady over time
    ribbon       both in one dict; TIGHTNESS lists the definitions of a "tight" ribbon
                 (mean width, max width, area) and score() reads one of them

The overall shape of a curve, and how two curves relate:

    fit          the simple function that fits a mean curve best (line, U / n,
                 L / J, peak / valley); it also predicts missing timepoints
    compare      opposite / similar / shifted / diverging / converging between the
                 fitted functions of two groups, or of two time windows of one curve

Input is always a matrix with one row per feature and one column per
timepoint, plus the timepoint labels and, optionally, their numeric times.
Nothing here knows about the dashboard or the cheese data. Which curves are
compared (clusters, sample groups, time windows) is left to the caller.
"""

from .changes import changes
from .compare import TOOLS, compare, strength, window
from .describe import describe, shape_of
from .divergence import divergence
from .fit import Fit, fit_curve
from .missingness import missingness
from .peaks import peaks
from .ribbon import MEASURES as RIBBON_MEASURES, METRIC as RIBBON_METRIC, TIGHTNESS, ribbon
from .ribbon import score as ribbon_score
from .spread import spread
from .timeaxis import TimeAxis
from .thresholds import Thresholds
from .trend import trend
from .width import width
from .width_trend import width_trend

__all__ = ["TimeAxis", "Thresholds", "trend", "peaks", "changes", "missingness", "spread",
           "divergence", "describe", "shape_of", "Fit", "fit_curve", "compare", "window", "strength",
           "TOOLS", "width", "width_trend", "ribbon", "ribbon_score", "TIGHTNESS", "RIBBON_MEASURES",
           "RIBBON_METRIC"]
