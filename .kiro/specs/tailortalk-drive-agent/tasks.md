# Tasks

## Implementation Plan

---

- [ ] **Task 1: Project scaffold and environment setup**
  - Create `backend/` and `frontend/` directory structure
  - Add `backend/.env.example` with `GROQ_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `DRIVE_FOLDER_ID`
  - Add `frontend/.streamlit/secrets.toml.example` with `BACKEND_URL`
  - Add `.gitignore` covering `.env`, `secrets.toml`, `*.json` key files, `__pycache__/`, `.venv/`
  - Create `backend/requirements.txt` and `frontend/requirements.txt`
  - _Requirement: 6_

- [ ] **Task 2: Pydantic schemas (`backend/schemas.py`)**
  - Define `FileResult` model: `id`, `name`, `mimeType`, `webViewLink`, `modifiedTime`
  - Define `ChatRequest` model: `message`, `session_id`
  - Define `ChatResponse` model: `response`, `files: List[FileResult]`, `session_id`
  - _Requirement: 6_

- [ ] **Task 3: Google Drive client (`backend/drive_client.py`)**
  - Load service account credentials from `GOOGLE_SERVICE_ACCOUNT_JSON` env var (parse JSON string)
  - Build Drive API v3 service with `drive.readonly` scope
  - Implement `search_files(q_string, folder_id, max_results=15)`:
    - Append `'{folder_id}' in parents and trashed = false` to every query
    - Call `files().list()` with `fields="files(id, name, mimeType, webViewLink, modifiedTime)"`
    - Order by `modifiedTime desc`
  - _Requirement: 1_

- [ ] **Task 4: Query builder (`backend/query_builder.py`)**
  - Define `MIME_TYPE_MAP` covering pdf, doc, docx, sheet, excel, image, png, jpg, presentation, pptx
  - Implement `build_query(name, file_type, content_query, date_after, date_before, relax_level=0)`:
    - Level 0: all filters active
    - Level 1: drop date filters
    - Level 2: drop date + type filters
    - Level 3: name/content only
  - Escape single quotes in name and content values
  - Return `"trashed = false"` when no filters are provided
  - _Requirement: 1, 2_

- [ ] **Task 5: LangGraph state schema (`backend/agent_state.py`)**
  - Define `AgentState` TypedDict with:
    - `messages: Annotated[list, add_messages]`
    - `raw_user_message: str`
    - `search_intent: Optional[dict]`
    - `q_string: Optional[str]`
    - `search_results: Optional[List[dict]]`
    - `attempt: int`
    - `final_response: Optional[str]`
    - `files: Optional[List[dict]]`
  - _Requirement: 1, 2, 3_

- [ ] **Task 6: Agent nodes (`backend/agent_nodes.py`)**
  - Initialise `ChatGroq` with `llama-3.3-70b-versatile`, `temperature=0`
  - Implement `parse_intent(state)`:
    - System prompt includes today's date for relative date resolution
    - Passes last 6 conversation turns for follow-up awareness
    - Strips markdown fences before `json.loads`; falls back to `{}`
  - Implement `build_query_node(state)`: calls `query_builder.build_query` with `relax_level=attempt`
  - Implement `search_drive_node(state)`: calls `drive_client.search_files`
  - Implement `should_retry(state) -> str`: returns `"retry"` if empty + attempt < 3, else `"format"`
  - Implement `increment_attempt(state)`: bumps `attempt` by 1
  - Implement `format_response(state)`: LLM writes 2–3 sentence summary; mentions retry if attempt > 0
  - _Requirement: 1, 2, 3, 4_

- [ ] **Task 7: LangGraph graph (`backend/agent_graph.py`)**
  - Build `StateGraph(AgentState)` with nodes: `parse_intent`, `build_query`, `search_drive`, `increment_attempt`, `format_response`
  - Wire edges: `parse_intent → build_query → search_drive`
  - Add conditional edge from `search_drive` using `should_retry`: `retry → increment_attempt`, `format → format_response`
  - Wire `increment_attempt → build_query` (retry loop)
  - Wire `format_response → END`
  - Export compiled `agent` singleton
  - _Requirement: 1, 2_

- [ ] **Task 8: FastAPI app (`backend/main.py`)**
  - Create FastAPI app with CORS middleware (`allow_origins=["*"]`)
  - Add `GET /health` returning `{"status": "ok"}`
  - Add `POST /chat` endpoint:
    - Retrieve session history from in-memory `sessions` dict
    - Invoke `agent` with full initial state
    - Append `HumanMessage` and `AIMessage` to history; trim to last 20
    - Serialize `files` list to `List[FileResult]`, skip malformed entries
    - Return `ChatResponse`
  - _Requirement: 3, 6_

- [ ] **Task 9: Streamlit frontend (`frontend/app.py`)**
  - Read `BACKEND_URL` from `st.secrets`
  - Define `MIME_ICONS` and `MIME_LABELS` dicts for all supported types
  - Implement `render_file_card(file)`:
    - 2-column layout: [icon + name + type/date caption] | [Open ↗ link button]
    - Followed by `st.divider()`
  - Implement `format_date(iso)` helper
  - Show suggested query buttons only when `st.session_state.messages` is empty
  - Handle suggested query click via `st.session_state.pending_message` + `st.rerun()`
  - Render full conversation history including file cards from `msg["files"]`
  - Call backend with 45s timeout; handle `Timeout`, `ConnectionError`, and generic exceptions separately
  - Add sidebar with session ID (truncated), clear button, and about text
  - _Requirement: 4, 5_

- [ ] **Task 10: Render deployment config (`render.yaml`)**
  - Define web service: root dir `backend/`, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`
  - Mark `GROQ_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `DRIVE_FOLDER_ID` as `sync: false`
  - _Requirement: 6_

- [ ] **Task 11: README with setup instructions**
  - Document Google Cloud service account setup steps
  - Show command to convert service account JSON to single-line string
  - Document Render backend deployment steps (5 steps)
  - Document Streamlit Cloud frontend deployment steps (4 steps)
  - Include example query table mapping natural language to Drive q strings
  - _Requirement: 6_

- [ ] **Task 12: End-to-end validation**
  - Verify `GET /health` returns 200
  - Test query: "find all PDFs" → confirms `mimeType = 'application/pdf'` in logs
  - Test query: "show me images" → confirms `mimeType contains 'image/'`
  - Test query: "documents about revenue" → confirms `fullText contains 'revenue'`
  - Test query that returns zero results → confirm fallback loop triggers and retries
  - Test follow-up message: "only from last week" → confirm date filter added to previous intent
  - Test "Clear conversation" button → confirm session resets
  - _Requirement: 1, 2, 3, 4, 5_
