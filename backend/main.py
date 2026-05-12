import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain.schema import HumanMessage, AIMessage

from schemas import ChatRequest, ChatResponse, FileResult
from agent_tool_based import run_agent

app = FastAPI(title="Dossier Drive Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session store ────────────────────────────────────────────────────
# Maps session_id → list of LangChain messages (conversation history)
sessions: dict = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Retrieve conversation history for this session
    history = sessions.get(req.session_id, [])

    try:
        result = run_agent(req.message, chat_history=history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    response_text = result.get("response") or "Sorry, something went wrong."
    files = result.get("files") or []

    # Persist updated history
    history.append(HumanMessage(content=req.message))
    history.append(AIMessage(content=response_text))
    # Keep last 20 messages to avoid token bloat on long sessions
    sessions[req.session_id] = history[-20:]

    # Serialize file results
    file_results = []
    for f in files:
        try:
            file_results.append(
                FileResult(
                    id=f["id"],
                    name=f["name"],
                    mimeType=f["mimeType"],
                    webViewLink=f.get("webViewLink", ""),
                    modifiedTime=f.get("modifiedTime"),
                )
            )
        except Exception:
            pass  # skip malformed entries

    return ChatResponse(
        response=response_text,
        files=file_results,
        session_id=req.session_id,
    )
