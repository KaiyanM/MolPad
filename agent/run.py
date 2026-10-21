"""Command line entry: python -m agent.run "question"

Prints the ordered steps (data actions, dashboard actions, messages) as JSON.
"""

import argparse
import json

from .graph import answer


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("question")
    p.add_argument("--state", help="current dashboard state as JSON, e.g. "
                   '\'{"min_weight": 1.5, "selected_clusters": ["Group_2", "Group_3"]}\'')
    p.add_argument("--brief", action="store_true", help="one line per step instead of JSON")
    p.add_argument("--play", action="store_true", help="one line of JSON with the dashboard and "
                   "message steps only, to paste into the dashboard chat box")
    p.add_argument("--debug", action="store_true", help="print each LLM decision, route and data "
                   "action as a [debug] line on stderr")
    a = p.parse_args()

    out = answer(a.question, json.loads(a.state) if a.state else None, debug=a.debug or None)
    if a.play:
        print(json.dumps([s for s in out["steps"] if s["kind"] != "data"]))
        return
    if not a.brief:
        print(json.dumps(out, indent=2))
        return
    print("trace:", json.dumps(out["trace"]))
    for i, s in enumerate(out["steps"], 1):
        if s["kind"] == "data":
            print(f"{i:2d}. data       {s['action']}  ->  {json.dumps(s['result'])[:160]}")
        elif s["kind"] == "dashboard":
            print(f"{i:2d}. dashboard  {s['command']}" + ("" if s["supported"] else "   [not supported yet]"))
        else:
            print(f"{i:2d}. message    {s['text']}")


if __name__ == "__main__":
    main()
