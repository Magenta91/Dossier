from langgraph.graph import StateGraph, END
from agent_state import AgentState
from agent_nodes import (
    parse_intent,
    build_query_node,
    search_drive_node,
    should_retry,
    increment_attempt,
    format_response,
)


def build_graph():
    graph = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("parse_intent", parse_intent)
    graph.add_node("build_query", build_query_node)
    graph.add_node("search_drive", search_drive_node)
    graph.add_node("increment_attempt", increment_attempt)
    graph.add_node("format_response", format_response)

    # ── Wire edges ────────────────────────────────────────────────────────────
    graph.set_entry_point("parse_intent")

    graph.add_edge("parse_intent", "build_query")
    graph.add_edge("build_query", "search_drive")

    # After search: either retry with relaxed query, or proceed to formatting
    graph.add_conditional_edges(
        "search_drive",
        should_retry,
        {
            "retry": "increment_attempt",
            "format": "format_response",
        },
    )

    # Retry loop: bump attempt counter → rebuild query → search again
    graph.add_edge("increment_attempt", "build_query")

    graph.add_edge("format_response", END)

    return graph.compile()


# Singleton agent — imported by main.py
agent = build_graph()
