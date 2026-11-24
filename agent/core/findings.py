"""Findings: a few short lines that say what a data action found. No LLM.

Every data step keeps two things apart:

    findings   these lines, which the message writer reads
    result     the full numbers (the evidence), which the dashboard shows on request

conclude(op, args, result) picks the rule for the data action. Lines name clusters
in dashboard order (Group_1 .. Group_10) and are never cut in the middle: when
they pass FINDINGS_CHARS, whole lines are dropped from the end and a last line
says how many are left in the evidence.
"""

FINDINGS_CHARS = 2000   # per data step, about 500 tokens


from .module import modules
from .text import _f, _groups, _list, _num, _order, _pct  # noqa: F401

# data operation -> rule; each module brings the rules for its own operations (modules/*/findings.py)
RULES = {op: rule for m in modules() for op, rule in m.rules.items()}


def fit(lines, limit=FINDINGS_CHARS):
    """Keep whole lines while they fit in `limit` characters; say how many were left out."""
    kept, used = [], 0
    for i, line in enumerate(lines):
        note = f"... {len(lines) - i} more lines in the evidence"
        if used + len(line) + 1 > limit - (len(note) if i < len(lines) - 1 else 0):
            return kept + [f"... {len(lines) - i} more lines in the evidence"]
        kept.append(line)
        used += len(line) + 1
    return kept


def conclude(op, args, result):
    """Findings of one data action: a short list of plain lines."""
    if isinstance(result, dict) and result.get("error"):
        return [f"failed: {result['error']}"]
    rule = RULES.get(op)
    if rule is None:
        return [f"{op}: no summary rule"]
    try:
        return fit(rule(args or {}, result))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:   # never stop the graph
        return [f"{op}: could not summarise ({type(exc).__name__}: {exc})"]
