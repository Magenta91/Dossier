from typing import TypedDict, Optional, List, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Full conversation history (auto-merged by LangGraph)
    messages: Annotated[list, add_messages]

    # Current user message (separate so nodes can reference it directly)
    raw_user_message: str

    # Structured intent extracted by the LLM (Node 1 output)
    search_intent: Optional[dict]

    # Drive API q string built by pure Python (Node 2 output)
    q_string: Optional[str]

    # Raw results from the Drive API (Node 3 output)
    search_results: Optional[List[dict]]

    # Tracks how many times we've relaxed the query (0–3)
    attempt: int

    # Final natural-language response (Node 5 output)
    final_response: Optional[str]

    # Files to surface in the UI
    files: Optional[List[dict]]
