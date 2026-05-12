# Design Document

## Overview

TailorTalk is split into two independently deployed services that communicate over HTTP.
The backend is a stateful LangGraph agent exposed via FastAPI. The frontend is a Streamlit
chat app that renders results as file cards.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│           Streamlit Cloud (Frontend)         │
│  ┌────────────────────────────────────────┐  │
│  │  app.py                                │  │
│  │  - Chat message history                │  │
│  │  - File result cards (icon/name/date)  │  │
│  │  - "Open ↗" links → webViewLink        │  │
│  │  - Suggested query buttons             │  │
│  │  - Sidebar: clear session              │  │
│  └──────────────┬─────────────────────────┘  │
└─────────────────│───────────────────────────-┘
                  │  POST /chat {message, session_id}
                  ▼
┌─────────────────────────────────────────────┐
│           Render (Backend / FastAPI)         │
│  ┌────────────────────────────────────────┐  │
│  │  main.py                               │  │
│  │  - In-memory session store             │  │
│  │  - Delegates to LangGraph agent        │  │
│  └──────────────┬─────────────────────────┘  │
│                 │                             │
│  ┌──────────────▼─────────────────────────┐  │
│  │  LangGraph Agent (agent_graph.py)      │  │
│  │                                        │  │
│  │  [1] parse_intent                      │  │
│  │       └─ LLM → structured JSON intent  │  │
│  │  [2] build_query                       │  │
│  │       └─ Pure Python → Drive q string  │  │
│  │  [3] search_drive                      │  │
│  │       └─ Drive API files.list          │  │
│  │  [edge] should_retry?                  │  │
│  │       ├─ retry → [4] increment_attempt │  │
│  │       │           └─ loop to [2]       │  │
│  │       └─ format → [5] format_response  │  │
│  │                    └─ LLM → prose      │  │
│  └────────────────────────────────────────┘  │
│                 │                             │
│  ┌──────────────▼─────────────────────────┐  │
│  │  Google Drive API v3                   │  │
│  │  files.list(q=..., fields=..., ...)    │  │
│  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## Component Design

### 1. Intent Parser (`parse_intent` node)

- **Input:** raw user message + last 6 conversation turns (for follow-up awareness)
- **LLM prompt:** instructs the model to return only valid JSON with keys:
  `name`, `file_type`, `content_query`, `date_after`, `date_before`
- **Relative date resolution:** prompt includes today's date so the LLM resolves
  "last month", "this week", etc. to ISO `YYYY-MM-DD` strings
- **Error handling:** strips markdown code fences before `json.loads`; falls back to `{}`

### 2. Query Builder (`query_builder.py`)

Pure Python — the LLM never writes Drive API syntax directly.

| Intent field | Drive q clause |
|---|---|
| `name` | `name contains 'value'` |
| `file_type` | `mimeType = 'application/pdf'` (exact) or `mimeType contains 'image/'` (prefix) |
| `date_after` | `modifiedTime > 'YYYY-MM-DDT00:00:00'` |
| `date_before` | `modifiedTime < 'YYYY-MM-DDT23:59:59'` |
| `content_query` | `fullText contains 'value'` |

**Relaxation levels** (controlled by `attempt` counter):
- Level 0 — all filters active
- Level 1 — date filters dropped
- Level 2 — date + type filters dropped
- Level 3 — name/content only (broadest)

Single quotes in values are escaped (`\'`) to prevent query injection.

### 3. Drive Client (`drive_client.py`)

- Authenticates using a Google Service Account JSON loaded from env var
- Always appends `'{FOLDER_ID}' in parents and trashed = false` to scope searches
- Returns up to 15 files ordered by `modifiedTime desc`
- Fields returned: `id`, `name`, `mimeType`, `webViewLink`, `modifiedTime`

### 4. Result Evaluator (conditional edge `should_retry`)

- Returns `"retry"` if `len(results) == 0 and attempt < 3`
- Returns `"format"` otherwise
- The retry path increments `attempt` and loops back to `build_query`

### 5. Response Formatter (`format_response` node)

- Builds a plain-text context block: user query + intent JSON + file list
- LLM writes a 2–3 sentence natural language summary
- If retries occurred, the summary mentions the query was broadened
- The raw file list is returned separately for the UI to render as cards

---

## State Schema (`agent_state.py`)

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # conversation history
    raw_user_message: str                      # current user input
    search_intent: Optional[dict]              # parsed intent (Node 1 output)
    q_string: Optional[str]                   # Drive q string (Node 2 output)
    search_results: Optional[List[dict]]       # raw Drive results (Node 3 output)
    attempt: int                               # relaxation level 0–3
    final_response: Optional[str]             # prose response (Node 5 output)
    files: Optional[List[dict]]               # files surfaced in UI
```

---

## API Contract

### `POST /chat`

**Request:**
```json
{ "message": "find budget PDFs", "session_id": "abc-123" }
```

**Response:**
```json
{
  "response": "I found 3 PDF files matching 'budget'.",
  "files": [
    {
      "id": "1abc...",
      "name": "Budget Report Q3.pdf",
      "mimeType": "application/pdf",
      "webViewLink": "https://drive.google.com/file/d/...",
      "modifiedTime": "2024-10-15T09:30:00.000Z"
    }
  ],
  "session_id": "abc-123"
}
```

### `GET /health`
```json
{ "status": "ok" }
```

---

## Frontend UI Structure (`app.py`)

```
Page header (TailorTalk logo + tagline)
    │
    ├── Suggested query buttons (visible only when chat is empty)
    │
    ├── Chat history (user + assistant messages)
    │       └── File result cards (per assistant message)
    │               ├── Icon + Name (bold)
    │               ├── Type label + Modified date (caption)
    │               └── "Open ↗" link button → webViewLink
    │
    ├── Chat input bar (sticky bottom)
    │
    └── Sidebar
            ├── Session ID (truncated)
            ├── Clear conversation button
            └── About text
```

---

## Sequence Diagram

```
User          Streamlit        FastAPI          LangGraph         Drive API
 │                │                │                 │                 │
 │─── message ───>│                │                 │                 │
 │                │─── POST /chat ─>│                 │                 │
 │                │                │─── invoke() ───>│                 │
 │                │                │                 │─ parse_intent ──│
 │                │                │                 │─ build_query    │
 │                │                │                 │─ search_drive ──────────>│
 │                │                │                 │<─ file results ──────────│
 │                │                │                 │─ [retry if empty, max 3x]│
 │                │                │                 │─ format_response│
 │                │<── response + files ─────────────│                 │
 │<── file cards ─│                │                 │                 │
```
