"""Compare the agent with the trace table of the decision tree (section 5).

    python -m agent.tests.eval_trace [--only Q15,Q22] [--workers 4] [--out results.json]
                                     [--pipeline tree|frame]

Needs an API key and makes about eight LLM calls per question. This is a
report of where the node prompts disagree with the tree, not a pass/fail test.
The node prompts quote some of these questions as examples, so agreement here
is an upper bound.
"""

import argparse
import csv
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from agent.graph import answer

QUESTIONS = Path(__file__).resolve().parents[2] / "development" / "questions"


def expected_rows():
    """Rows of the section-5 table: Q, N1, N2, N3 filters, N4 selector, N5 descriptor, Leaf."""
    rows = {}
    for line in (QUESTIONS / "cheese_decision_tree.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and re.fullmatch(r"Q\d\d", cells[0]):
            rows[cells[0]] = cells[1:]
    return rows


def _keys(text, table):
    text = text.lower()
    return sorted({name for key, name in table if key in text})


def expected(cells):
    n1, n2, n3, n4, n5, leaf = cells
    code = re.search(r"L\d", leaf).group(0)
    exp = {"leaf": code, "N0": {"L0": "out_of_scope", "L1": "design"}.get(code, "data")}
    if exp["N0"] != "data":
        return exp
    exp["N1"] = {"ok": "ok", "ask": "ask", "assume default": "assume_default",
                 "current selection": "use_current_selection"}[n1]
    if exp["N1"] == "ask":
        return exp
    exp["N2"] = n2.replace(" ", "_")
    n3 = "" if n3.startswith("none") else re.sub(r"\(.*?\)", "", n3)
    exp["N3"] = _keys(n3, [("cols", "cols"), ("level1", "level1"), ("level2", "level2"),
                           ("level3", "level3"), ("external", "external"), ("contrast", "contrast")])
    exp["N4"] = _keys(n4, [("pattern", "pattern"), ("feature number", "feature_number"),
                           ("network", "network"), ("weight", "network"),
                           ("feature lookup", "feature_lookup"), ("given", "given"), ("all", "all")])
    exp["N5"] = _keys(n5, [("pattern", "pattern"), ("level2", "level2"), ("level3", "level3"),
                           ("weight", "weight"), ("feature number", "feature_number")])
    return exp


def actual(trace):
    act = {k: trace[k] for k in ("leaf", "N0", "N1", "N2") if k in trace}
    if "N3" not in trace:
        return act
    many = isinstance(trace["N3"], list)
    f3 = trace["N3"] if many else [trace["N3"]]
    f4 = trace["N4"] if many else [trace["N4"]]
    f5 = trace["N5"] if many else [trace["N5"]]
    n3 = set()
    for f in f3:
        n3 |= {k for k in ("cols", "level1", "level2") if f.get(k)}
        if f.get("level3_column"):
            n3.add("level3")
        if f.get("external_concept"):
            n3.add("external")
        if f.get("contrast", "none") != "none":
            n3.add("contrast")
    if many and len({tuple(f.get("level1") or []) for f in f3}) > 1:
        n3.add("contrast")
    act["N3"] = sorted(n3)
    act["N4"] = sorted({s["kind"] for steps in f4 for s in steps
                        if s.get("criterion") or s["kind"] not in ("pattern", "network")} or {"all"})
    n5 = set()
    for d in f5:
        n5 |= {k for k in ("pattern", "level2", "weight", "feature_number") if d.get(k)}
        if d.get("level3_column"):
            n5.add("level3")
    act["N5"] = sorted(n5)
    return act


def run_one(qid, question):
    try:
        out = answer(question)
        return qid, out, None
    except Exception as exc:
        return qid, None, f"{type(exc).__name__}: {exc}"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--only", help="comma-separated question ids")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--out", help="write full outputs to this JSON file")
    p.add_argument("--pipeline", choices=("tree", "frame"), help="sets AGENT_PIPELINE for this run")
    a = p.parse_args()
    if a.pipeline:
        os.environ["AGENT_PIPELINE"] = a.pipeline

    table = expected_rows()
    with open(QUESTIONS / "cheese_questions.csv", encoding="utf-8", errors="replace") as fh:
        questions = {r["id"]: r["question"] for r in csv.DictReader(fh) if r["id"] in table}
    if a.only:
        questions = {q: questions[q] for q in a.only.split(",")}

    with ThreadPoolExecutor(a.workers) as pool:
        results = list(pool.map(lambda kv: run_one(*kv), questions.items()))

    nodes = ("N0", "N1", "N2", "N3", "N4", "N5", "leaf")
    hits = {n: [0, 0] for n in nodes}
    full, costs = {}, []
    for qid, out, err in results:
        exp = expected(table[qid])
        if err:
            print(f"{qid}  ERROR {err}")
            full[qid] = {"error": err}
            continue
        act = actual(out["trace"])
        wrong = []
        for n in nodes:
            if n not in exp:
                continue
            hits[n][1] += 1
            if act.get(n) == exp[n]:
                hits[n][0] += 1
            else:
                wrong.append(f"{n}: expected {exp[n]}, got {act.get(n)}")
        c = out["trace"].get("cost") or {}
        if c:
            costs.append(c)
        tag = f"[{c.get('calls', '?')} calls, {c.get('output_tokens', 0):.0f} out tok, {c.get('wall_seconds', 0):.0f}s]"
        print(f"{qid}  {tag:34s} {'ok' if not wrong else '; '.join(wrong)}")
        full[qid] = {"question": questions[qid], "expected": exp, "actual": act, **out}

    print("\nAgreement with the trace table")
    for n in nodes:
        print(f"  {n:5s} {hits[n][0]:2d} / {hits[n][1]:2d}")
    if costs:
        n = len(costs)
        mean = {k: sum(c.get(k, 0) for c in costs) / n
                for k in ("calls", "input_tokens", "output_tokens", "reasoning_tokens", "wall_seconds")}
        print(f"\nMean per question ({n}): {mean['calls']:.1f} LLM calls, {mean['input_tokens']:.0f} input / "
              f"{mean['output_tokens']:.0f} output tokens ({mean['reasoning_tokens']:.0f} reasoning), "
              f"{mean['wall_seconds']:.1f}s wall")
    if a.out:
        Path(a.out).write_text(json.dumps(full, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
