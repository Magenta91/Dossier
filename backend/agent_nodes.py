import os
import json
from datetime import datetime
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage
from query_builder import build_query
from drive_client import search_files
from agent_state import AgentState

# ── LLM setup ────────────────────────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

# ── Prompts ───────────────────────────────────────────────────────────────────
INTENT_SYSTEM_PROMPT = f"""You are a Google Drive search assistant. Today's date is {datetime.now().strftime("%Y-%m-%d")}.

Your job: extract the user's file search intent from their message and return it as a JSON object.

Fields to extract (omit any that aren't mentioned or implied):
- name        : keyword(s) to search in the filename (string) — USE THIS for any words that describe what files to find
- file_type   : one of [pdf, doc, docx, gdoc, sheet, gsheet, excel, xlsx, image, png, jpg, presentation, gslides, pptx] (string)
- content_query : keywords to search WITHIN file content (string) — only use when user explicitly says "contains", "mentions", "about", etc.
- date_after  : ISO date string YYYY-MM-DD — files modified after this date (string)
- date_before : ISO date string YYYY-MM-DD — files modified before this date (string)

Rules:
- When user asks for files by name/topic (e.g. "reports", "invoices", "budget"), put it in the "name" field.
- Only use "content_query" when user explicitly wants to search INSIDE files (e.g. "files that mention X").
- Resolve relative dates (e.g. "last month", "last week", "yesterday") using today's date.
- If the user says "find everything" or "list all files", return an empty object {{}}.
- For follow-up messages referencing previous results (e.g. "only PDFs of those"), combine with prior intent.
- Return ONLY valid JSON — no markdown, no explanation, no code fences.

Examples:
User: "find the budget report pdf from last month"
Response: {{"name": "budget report", "file_type": "pdf", "date_after": "2024-10-01", "date_before": "2024-10-31"}}

User: "show me all images"
Response: {{"file_type": "image"}}

User: "show me reports"
Response: {{"name": "reports"}}

User: "find invoices"
Response: {{"name": "invoices"}}

User: "documents that mention quarterly revenue"
Response: {{"content_query": "quarterly revenue"}}

User: "find invoice excel files modified this week"
Response: {{"name": "invoice", "file_type": "excel", "date_after": "{datetime.now().strftime('%Y-%m-%d')}"}}
"""

RESPONSE_SYSTEM_PROMPT = """You are a helpful, friendly Google Drive assistant called TailorTalk.

Given the user's request and the search results, write a natural, concise response.

Guidelines:
- If files were found: briefly describe what was found (count, types), then let the UI show the file cards.
- If no files were found: say so warmly, and suggest 1-2 alternate search strategies.
- Never make up file names or invent results.
- Keep responses to 2-3 sentences max.
- Do not list file names in your text — the UI renders file cards separately."""


# ── Node 1: Parse Intent ──────────────────────────────────────────────────────
def parse_intent(state: AgentState) -> AgentState:
    """LLM extracts structured search intent from the user message + history."""
    # Build message list: system + conversation history + current message
    messages = [SystemMessage(content=INTENT_SYSTEM_PROMPT)]

    # Include recent conversation history for follow-up awareness (last 6 turns)
    for msg in state.get("messages", [])[-6:]:
        messages.append(msg)

    messages.append(HumanMessage(content=state["raw_user_message"]))

    response = llm.invoke(messages)

    try:
        text = response.content.strip()
        # Strip markdown code fences if the LLM added them
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.lower().startswith("json"):
                text = text[4:]
        intent = json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        intent = {}

    return {**state, "search_intent": intent, "attempt": 0}


# ── Node 2: Build Query ───────────────────────────────────────────────────────
def build_query_node(state: AgentState) -> AgentState:
    """Pure Python: converts structured intent → Drive API q string. No LLM."""
    intent = state.get("search_intent") or {}
    attempt = state.get("attempt", 0)

    q = build_query(
        name=intent.get("name"),
        file_type=intent.get("file_type"),
        content_query=intent.get("content_query"),
        date_after=intent.get("date_after"),
        date_before=intent.get("date_before"),
        relax_level=attempt,
    )

    return {**state, "q_string": q}


# ── Node 3: Search Drive ──────────────────────────────────────────────────────
def search_drive_node(state: AgentState) -> AgentState:
    """Executes the Drive API files.list query."""
    q = state.get("q_string") or "trashed = false"
    folder_id = os.getenv("DRIVE_FOLDER_ID", "")
    results = search_files(q, folder_id=folder_id)
    return {**state, "search_results": results}


# ── Conditional Edge: Should we retry with a relaxed query? ───────────────────
def should_retry(state: AgentState) -> str:
    """
    Returns 'retry' if results are empty and we haven't hit max attempts.
    Returns 'format' otherwise.
    """
    results = state.get("search_results") or []
    attempt = state.get("attempt", 0)

    if len(results) == 0 and attempt < 3:
        return "retry"
    return "format"


# ── Node 4: Increment Attempt (used on retry path) ────────────────────────────
def increment_attempt(state: AgentState) -> AgentState:
    """Bumps the attempt counter before re-running the query builder."""
    return {**state, "attempt": state.get("attempt", 0) + 1}


# ── Node 5: Format Response ───────────────────────────────────────────────────
def format_response(state: AgentState) -> AgentState:
    """LLM writes a natural language summary of the search results."""
    results = state.get("search_results") or []
    intent = state.get("search_intent") or {}
    attempt = state.get("attempt", 0)

    # Build context for the LLM
    context_lines = [f"User asked: {state['raw_user_message']}"]
    if intent:
        context_lines.append(f"Interpreted as: {json.dumps(intent)}")
    if attempt > 0:
        context_lines.append(f"Note: query was relaxed {attempt} time(s) to find results.")

    if results:
        context_lines.append(f"\nFound {len(results)} file(s):")
        for f in results:
            modified = f.get("modifiedTime", "unknown date")
            context_lines.append(f"  - {f['name']} ({f['mimeType']}) modified {modified}")
    else:
        context_lines.append("\nNo files found after trying 3 progressively broader queries.")

    context = "\n".join(context_lines)

    response = llm.invoke(
        [SystemMessage(content=RESPONSE_SYSTEM_PROMPT), HumanMessage(content=context)]
    )

    return {
        **state,
        "final_response": response.content,
        "files": results,
    }
