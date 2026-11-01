"""Read the dashboard data that gDashboard_d3() writes, and the optional context file.

    read_payload(path)   the JSON of a dashboard page (.html) or a plain .json payload
    read_context(path)   what R does not know about the data, for the LLM (see contexts/)
    load(dashboard, context)  both, as a Dataset
"""

import json
import re
from dataclasses import fields, replace
from pathlib import Path

from .config import LevelConfig

_TAG = re.compile(r'<script[^>]*id="molpad-data"[^>]*>(.*?)</script>', re.S)

# Keys a context file may set (fields of LevelConfig that describe the data in words).
CONTEXT_KEYS = ("background", "level1_name", "level2_name", "missing")


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
    """A LevelConfig with the context file's descriptions; generic ones without a file."""
    cfg = LevelConfig(background="Longitudinal data shown in a MolPad dashboard. Features are "
                                 "grouped into clusters by the shape of their trajectory.",
                      level1_name="functional annotation", level2_name="taxonomic scope")
    if path is None:
        return cfg
    ctx = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = set(ctx) - set(CONTEXT_KEYS)
    if unknown:
        raise ValueError(f"unknown keys in {path}: {sorted(unknown)}; allowed: {list(CONTEXT_KEYS)}")
    names = {f.name for f in fields(LevelConfig)}
    return replace(cfg, **{k: v for k, v in ctx.items() if k in names})


def load(dashboard, context=None):
    from .data_tools import Dataset

    payload = read_payload(dashboard)
    cfg = read_context(context)
    if context is None and payload.get("title"):
        cfg = replace(cfg, background=f"{payload['title']}. " + cfg.background)
    ds = Dataset.from_payload(payload, cfg)
    ds.title = payload.get("title")
    return ds
