"""The decision tree as a LangGraph.

    START -> keywords -> n0_kind -> leaf_L0 | leaf_L1 | n1_completeness
    n1_completeness -> leaf_L2 | n2_shape
    n2_shape -> n3_filters -> n4_selector -> n5_descriptor -> run_data
    run_data -> n3_filters (next sub-claim) | n6_display
    n6_display, leaf_L0, leaf_L1, leaf_L2 -> compose_messages -> END
"""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from . import nodes
from .data_tools import load_dataset


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(nodes.AgentState)
    for name in ("keywords", "n0_kind", "n1_completeness", "n2_shape", "n3_filters", "n4_selector", "n5_descriptor",
                 "run_data", "n6_display", "leaf_L0", "leaf_L1", "leaf_L2", "compose_messages"):
        g.add_node(name, getattr(nodes, name))

    g.add_edge(START, "keywords")
    g.add_edge("keywords", "n0_kind")
    g.add_conditional_edges("n0_kind", nodes.route_n0, ["leaf_L0", "leaf_L1", "n1_completeness"])
    g.add_conditional_edges("n1_completeness", nodes.route_n1, ["leaf_L2", "n2_shape"])
    g.add_edge("n2_shape", "n3_filters")
    g.add_edge("n3_filters", "n4_selector")
    g.add_edge("n4_selector", "n5_descriptor")
    g.add_edge("n5_descriptor", "run_data")
    g.add_conditional_edges("run_data", nodes.route_loop, ["n3_filters", "n6_display"])
    for name in ("n6_display", "leaf_L0", "leaf_L1", "leaf_L2"):
        g.add_edge(name, "compose_messages")
    g.add_edge("compose_messages", END)
    return g.compile()


def _one(items):
    return items[0] if len(items) == 1 else items


def answer(question: str, dash_state: dict | None = None, debug: bool | None = None) -> dict:
    """Run one question. Returns the ordered steps and the path taken through the tree.

    debug=True prints one "[debug]" line per LLM decision, route and data action to stderr.
    """
    if debug is not None:
        nodes.DEBUG = debug
    state = {**load_dataset().default_state(), **(dash_state or {})}
    final = build_graph().invoke({"question": question, "dash_state": state},
                                 {"recursion_limit": 60})
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
    return {"question": question, "trace": trace, "steps": final["steps"]}
