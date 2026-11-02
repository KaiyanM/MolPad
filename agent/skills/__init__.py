"""Skill cards for the plan call: one card per condition, picked by code from the question's roles.

core.md is always loaded. The others are loaded only when a role asks for them, so a network
question does not read the ribbon and compare rules. When the roles give nothing to go on, every
card is loaded and the plan call sees the same rules the tree pipeline does.
"""

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent
CARDS = ("pattern", "compare", "ribbon", "feature_number", "network", "lookup", "example", "given")

# selector kind -> card
_BY_TARGET = {"pattern": "pattern", "ribbon": "ribbon", "feature_number": "feature_number",
              "network": "network", "feature_lookup": "lookup", "example": "example", "given": "given"}


@lru_cache(maxsize=None)
def card(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def pick_skills(frames, status="ok", kmap=None):
    """Card names for a list of frames (dicts with target / measure / compare / mentions).

    `status` is the N1 status of the question; `kmap` the keyword map from keywords.map_keywords.
    """
    picked = []

    def add(name):
        if name not in picked:
            picked.append(name)

    for f in frames:
        for kind in f.get("target") or []:
            if kind in _BY_TARGET:
                add(_BY_TARGET[kind])
        if f.get("compare") == "curves":
            add("pattern")
            add("compare")
        measure = f.get("measure") or []
        if "weight" in measure:
            add("network")
        if "level3" in measure or f.get("outside_concept"):
            add("lookup")
    if status == "use_current_selection":
        add("given")
    for k in (kmap or {}).get("keywords", []):
        levels = {m["level"] for m in k["matches"]}
        if "cluster" in levels:
            add("given")
        if "level3" in levels:
            add("lookup")
    if not picked and not any(f.get("target") for f in frames):
        # no rule was read: "all" needs no card, but a wrong guess here is costly, so keep every card
        # only when nothing at all (no measure either) was read
        if not any(f.get("measure") for f in frames):
            return list(CARDS)
    return [c for c in CARDS if c in picked]


def plan_prompt(names) -> str:
    return "\n\n".join([card("core")] + [card(n) for n in names])
