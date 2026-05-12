---
inclusion: always
---

# TailorTalk — Tech Stack

## Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI + Uvicorn
- **Agent Framework:** LangGraph (stateful graph with conditional edges)
- **LLM:** Groq API — model `llama-3.3-70b-versatile`
- **LangChain:** `langchain`, `langchain-groq` for LLM calls and message schemas
- **Drive Integration:** Google Drive API v3 — `google-api-python-client`, Service Account auth
- **Config:** `python-dotenv`

## Frontend
- **Framework:** Streamlit 1.39+
- **Communication:** HTTP POST to FastAPI `/chat` endpoint via `requests`

## Deployment
- **Backend:** Render Web Service — root dir `backend/`, start cmd `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Frontend:** Streamlit Cloud — main file `frontend/app.py`

## Environment Variables

| Variable | Where set | Description |
|---|---|---|
| `GROQ_API_KEY` | Render env vars | Groq API key |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Render env vars | Full service account JSON as one-line string |
| `DRIVE_FOLDER_ID` | Render env vars | Google Drive folder ID to scope searches |
| `BACKEND_URL` | Streamlit secrets | Full Render URL, e.g. `https://tailortalk.onrender.com` |

## Critical Architectural Rules

1. **LLM never writes raw Drive `q` syntax.** `query_builder.py` owns query construction in pure Python.
2. **Intent is always a typed dict** — keys: `name`, `file_type`, `content_query`, `date_after`, `date_before`.
3. **All backend files live flat in `backend/`** — use absolute imports only, no relative imports.
4. **Session state is in-memory** — `dict[session_id → list[LangChain messages]]`, trimmed to last 20.
5. **Never use `<form>` tags** in any frontend HTML/React code.
6. **Never commit secrets** — `.env`, `secrets.toml`, and service account JSON files are in `.gitignore`.
