"""Run one question through the pipeline (agent/frame.py) and return its steps and trace."""

import time

from . import nodes
from .data_tools import load_dataset


def _graph():
    from .frame import build_frame_graph
    return build_frame_graph()


def _one(items):
    return items[0] if len(items) == 1 else items


def answer(question: str, dash_state: dict | None = None, debug: bool | None = None,
           on_event=None) -> dict:
    """Run one question. Returns the ordered steps and the decisions taken (named N0..N6 after the
    nodes of development/questions/cheese_decision_tree.md).

    debug=True prints one "[debug]" line per LLM decision, route and data action to stderr.

    on_event(dict) is called while the answer is built, so a client need not wait for the end:
        {"event": "status", "text"}          what the agent is doing now
        {"event": "plan",   "text"}          the sub-questions (a question that was split only)
        {"event": "steps",  "steps"}         the whole playback: one "unit" step opens each
                                             (sub-)question; a message is {"slot", "text": None}
        {"event": "text",   "slot", "text"}  the text of one message, as soon as it is written
        {"event": "done",   "trace"}
    The times of the first event, of "steps" (the first dashboard action can start) and of the
    first text are in trace["cost"], with or without on_event.
    """
    from .llm import start_usage, usage_summary

    if debug is not None:
        nodes.DEBUG = debug
    state = {**load_dataset().default_state(), **(dash_state or {})}
    log = start_usage()
    t0 = time.time()
    first = {}

    def emit(event):
        first.setdefault("first_event_seconds", round(time.time() - t0, 1))
        if event["event"] in ("steps", "text"):
            first.setdefault(f"first_{event['event']}_seconds", round(time.time() - t0, 1))
        if on_event is not None:
            on_event(event)

    token = nodes.EMIT.set(emit)
    try:
        final = _graph().invoke({"question": question, "dash_state": state}, {"recursion_limit": 60})
    finally:
        nodes.EMIT.reset(token)
    cost = {**usage_summary(log), "wall_seconds": round(time.time() - t0, 1), **first}
    units = final.get("units") or []
    trace = {"keywords": final["keyword_map"], "N0": final["kind"]["kind"]}
    if "completeness" in final:
        trace["N1"] = final["completeness"]["status"]
    if "shape" in final:
        trace["N2"] = final["shape"]
        if len(final["sub_questions"]) > 1:
            trace["sub_claims"] = final["sub_questions"]
    if units:
        trace["N3"] = _one([u["filters"] for u in units])
        trace["N4"] = _one([u["selector"]["steps"] for u in units])
        trace["N5"] = _one([u["descriptor"] for u in units])
    if "display" in final:
        trace["N6"] = final["display"]
    trace["leaf"] = final["leaf"]
    if final.get("skills") is not None:
        trace["skills"] = final["skills"]
    trace["cost"] = cost
    nodes._debug("cost", f"{cost['calls']} LLM calls, {cost['input_tokens']:.0f} in / "
                 f"{cost['output_tokens']:.0f} out ({cost['reasoning_tokens']:.0f} reasoning) tokens, "
                 f"{cost['seconds']:.1f}s in LLM, {cost['wall_seconds']:.1f}s total")
    nodes._debug("cost", f"first event {first.get('first_event_seconds')}s, playback ready "
                 f"{first.get('first_steps_seconds')}s, first text {first.get('first_text_seconds')}s")
    if on_event is not None:
        on_event({"event": "done", "trace": trace})
    return {"question": question, "trace": trace, "steps": final["steps"]}
