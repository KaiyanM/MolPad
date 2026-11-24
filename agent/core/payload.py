"""Read the dashboard data that gDashboard_d3() writes, and the optional context file.

    read_payload(path)   the JSON of a dashboard page (.html) or a plain .json payload
    read_context(path)   entries that overrule the page's `dataset` block (see contexts/)
    load(dashboard, context)  both, as a Dataset
"""

import json
import re
from pathlib import Path

from . import datacard

_TAG = re.compile(r'<script[^>]*id="molpad-data"[^>]*>(.*?)</script>', re.S)

# Keys a context file may set: those of the page's `dataset` block, and two older names.
CONTEXT_KEYS = datacard.KEYS + tuple(datacard.OLD_KEYS)


def read_payload(path):
    """The dashboard JSON from an index.html written by gDashboard_d3(), or from a .json file."""
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix.lower() in (".html", ".htm"):
        m = _TAG.search(text)
        if not m:
            raise ValueError(f"{path} has no <script id=\"molpad-data\"> tag; is it a MolPad dashboard?")
        text = m.group(1)                  # "<\/" inside it is a valid JSON escape
    payload = json.loads(text)
    for key in ("timepoints", "features", "clusters"):
        if key not in payload:
            raise ValueError(f"the dashboard data has no '{key}'")
    return payload


def read_context(path=None):
    """The entries of a context file, checked; {} without a file."""
    if path is None:
        return {}
    return datacard.normalise(json.loads(Path(path).read_text(encoding="utf-8")), str(path))


def load(dashboard, context=None):
    """The dataset of a page. What the data is comes from the page's `dataset` block; the
    context file overrules it, entry by entry. A page without a block gets generic words."""
    from .data_tools import Dataset

    payload = read_payload(dashboard)
    ctx = read_context(context)
    described = "background" in ctx or "background" in (payload.get("dataset") or {})
    if not described and payload.get("title"):
        ctx = {**ctx, "background": f"{payload['title']}. " + datacard.GENERIC["background"]}
    ds = Dataset.from_payload(payload, context=ctx)
    ds.title = payload.get("title")
    return ds
