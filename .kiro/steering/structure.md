---
inclusion: always
---

# TailorTalk — Project Structure

```
tailor-talk/
├── backend/                     # FastAPI backend → deployed on Render
│   ├── main.py                  # App entry point, /chat endpoint, session store
│   ├── schemas.py               # Pydantic models: ChatRequest, ChatResponse, FileResult
│   ├── drive_client.py          # Google Drive API files.list wrapper
│   ├── query_builder.py         # Pure Python Drive q-string builder (no LLM)
│   ├── agent_state.py           # LangGraph TypedDict state schema
│   ├── agent_nodes.py           # All 5 agent nodes + conditional edge function
│   ├── agent_graph.py           # LangGraph graph wiring; exports `agent` singleton
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                    # Streamlit frontend → deployed on Streamlit Cloud
│   ├── app.py                   # Chat UI, file result cards, suggested queries, sidebar
│   ├── requirements.txt
│   └── .streamlit/
│       └── secrets.toml.example
│
├── .kiro/                       # Kiro spec-driven development files
│   ├── steering/                # Persistent AI context (always loaded)
│   │   ├── product.md
│   │   ├── tech.md
│   │   └── structure.md
│   ├── specs/
│   │   └── tailortalk-drive-agent/
│   │       ├── requirements.md
│   │       ├── design.md
│   │       └── tasks.md
│   └── hooks/
│       └── code-quality.json
│
├── render.yaml                  # Render deployment config
├── .gitignore
└── README.md
```

## LangGraph Agent Flow

```
parse_intent → build_query → search_drive → [should_retry?]
                                                 │ retry → increment_attempt → build_query (loop)
                                                 │ format → format_response → END
```

## Key File Roles

| File | Responsibility |
|---|---|
| `agent_nodes.py` | All business logic — LLM calls, Drive search, fallback |
| `query_builder.py` | Single source of truth for Drive API q strings |
| `drive_client.py` | All Google Drive API communication |
| `agent_graph.py` | Graph topology only — no business logic |
| `main.py` | HTTP interface only — delegates everything to `agent` |
