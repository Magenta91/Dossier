# 🗂️  AI-Powered Google Drive Assistant

A conversational AI agent that searches, filters, and discovers files in Google Drive using natural language.

## Architecture

```
User
 │
 ▼
Streamlit (Streamlit Cloud)
 │  HTTP POST /chat
 ▼
FastAPI (Render)
 │
 ▼
LangGraph Agent
 ├─ Node 1: Intent Parser      → LLM extracts structured JSON from user message
 ├─ Node 2: Query Builder      → Pure Python builds Drive API `q` string (no hallucinations)
 ├─ Node 3: Drive Search       → files.list API call
 ├─ Conditional Edge           → Zero results? Relax query and retry (up to 3x)
 └─ Node 5: Response Formatter → LLM writes natural language summary
```

**Query relaxation levels:**
- Level 0 — Full query (name + type + date + content)
- Level 1 — Drop date filters
- Level 2 — Drop date + type filters
- Level 3 — Name / content only (broadest)

---

## Setup

### 1. Prerequisites
- Python 3.11+
- A Google Cloud project
- A Groq API key (free at https://console.groq.com)

### 2. Google Drive Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project → Enable **Google Drive API**
3. Go to **IAM & Admin → Service Accounts** → Create a service account
4. Create a JSON key for the service account → download it
5. Copy the [sample Drive folder](https://drive.google.com/drive/folders/1qkx58doSeYrcLjHPDysJyVJ36PsSqqlt) into your own Drive
6. Share the copied folder with the service account's email (Viewer permission)

### 3. Backend (local)

```bash
cd backend
cp .env.example .env
# Edit .env: paste your GROQ_API_KEY, service account JSON, and DRIVE_FOLDER_ID

pip install -r requirements.txt
uvicorn main:app --reload
# → runs on http://localhost:8000
```

**Setting `GOOGLE_SERVICE_ACCOUNT_JSON`:**
The value must be the *entire contents* of your service account JSON file, on a single line:
```bash
# Quick way to get the single-line version:
cat your-service-account.json | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)))"
```

### 4. Frontend (local)

```bash
cd frontend
pip install -r requirements.txt

mkdir -p .streamlit
echo 'BACKEND_URL = "http://localhost:8000"' > .streamlit/secrets.toml

streamlit run app.py
# → opens http://localhost:8501
```

---

## Deployment

### Backend → Render
Backend is deployed at render, just add a additional variable of Python version : 3.11, there are some dependency conflict, with pydantic core with python 3.14.
https://dossier-q74p.onrender.com is the backend link.

### Frontend → Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repo
3. Set **Main file path** to `frontend/app.py`
4. Under **Advanced → Secrets**, add:
   ```toml
   BACKEND_URL = "https://your-render-backend.onrender.com"
   ```
5. Deploy → get your `https://your-app.streamlit.app` URL

---

## Example Queries

| User says | Drive query built |
|---|---|
| "find budget PDFs" | `name contains 'budget' and mimeType = 'application/pdf'` |
| "images from last month" | `mimeType contains 'image/' and modifiedTime > '...' and modifiedTime < '...'` |
| "docs mentioning quarterly revenue" | `fullText contains 'quarterly revenue'` |
| "invoices modified this week" | `name contains 'invoice' and modifiedTime > '...'` |
| "show me everything" | *(folder-scoped, no filters)* |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Agent | LangGraph (stateful graph with fallback loop) |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Drive API | Google Drive API v3 (`files.list` + `q` parameter) |
| Frontend | Streamlit |
| Backend host | Render |
| Frontend host | Streamlit Cloud |
