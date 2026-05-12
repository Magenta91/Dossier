# 🗂️ Dossier — AI-Powered Google Drive Assistant

A conversational AI agent that searches, filters, and discovers files in Google Drive using natural language. Built with LangChain tool calling and direct Drive API query generation.

## 🌐 Live Demo

- **Frontend**: https://dossier-drive-assistant.streamlit.app/
- **Backend API**: https://dossier-q74p.onrender.com

Try it now! Ask questions like:
- "Find all PDF reports"
- "Show me spreadsheets from last month"
- "Documents that mention budget"

## 🏗️ Architecture

```
User Query: "Find budget reports from last week"
 │
 ▼
Streamlit Frontend (Streamlit Cloud)
 │  HTTP POST /chat
 ▼
FastAPI Backend (Render)
 │
 ▼
LangChain Tool-Calling Agent
 │
 ├─ LLM generates Drive API query string:
 │  "(name contains 'budget' or name contains 'report') 
 │   and modifiedTime > '2024-05-05T00:00:00' 
 │   and trashed = false 
 │   and mimeType != 'application/vnd.google-apps.folder'"
 │
 ▼
DriveSearchTool
 │
 ▼
Google Drive API (files.list)
 │  - Recursive folder search
 │  - Filters by q parameter
 │
 ▼
Results → LLM formats response → User
```

### 🎯 Key Features

- **Direct Query Generation**: LLM writes Drive API `q` parameter strings directly (no intermediate JSON)
- **Full Drive API Power**: Supports complex queries with `and`/`or`/parentheses
- **Smart Search**: 
  - Name search: `name contains 'keyword'`
  - Content search: `fullText contains 'keyword'`
  - Type filtering: `mimeType = 'application/pdf'`
  - Date filtering: `modifiedTime > '2024-01-01T00:00:00'`
- **Recursive Folder Search**: Finds files in subfolders automatically
- **Plural/Singular Handling**: "reports" finds both "report" and "reports"
- **Auto-Retry**: If no results, agent automatically broadens search criteria
- **Tool-Based Architecture**: Uses LangChain function calling for transparency

---

## 🚀 Setup

### 1. Prerequisites
- Python 3.11+
- A Google Cloud project with Drive API enabled
- A Groq API key (free at https://console.groq.com)

### 2. Google Drive Setup

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable **Google Drive API**

2. **Create Service Account**
   - Go to **IAM & Admin → Service Accounts**
   - Create a service account
   - Create a JSON key → download it

3. **Share Drive Folder**
   - Create or use an existing Google Drive folder
   - Share it with the service account's email (Viewer permission)
   - Copy the folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

### 3. Backend (Local Development)

```bash
cd backend
cp .env.example .env
# Edit .env with your credentials:
# - GROQ_API_KEY
# - GOOGLE_SERVICE_ACCOUNT_JSON (entire JSON as single line)
# - DRIVE_FOLDER_ID

pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# → Backend runs on http://localhost:8000
```

**💡 Tip: Converting service account JSON to single line:**
```bash
cat your-service-account.json | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)))"
```

### 4. Frontend (Local Development)

```bash
cd frontend
pip install -r requirements.txt

# Create secrets file
mkdir -p .streamlit
echo 'BACKEND_URL = "http://localhost:8000"' > .streamlit/secrets.toml

streamlit run app.py
# → Frontend opens at http://localhost:8501
```

---

## 🌐 Deployment

### Backend → Render

1. **Create Web Service**
   - Connect your GitHub repository
   - Set **Root Directory**: `backend`
   - Set **Build Command**: `pip install -r requirements.txt`
   - Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

2. **Environment Variables**
   ```
   PYTHON_VERSION = 3.11
   GROQ_API_KEY = your_groq_api_key
   GOOGLE_SERVICE_ACCOUNT_JSON = {"type":"service_account",...}
   DRIVE_FOLDER_ID = your_folder_id
   ```

3. **Important**: Set `PYTHON_VERSION=3.11` to avoid pydantic-core compilation issues with Python 3.14

**Live Backend**: https://dossier-q74p.onrender.com

### Frontend → Streamlit Cloud

1. **Deploy App**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repo
   - Set **Main file path**: `frontend/app.py`

2. **Add Secrets** (Settings → Secrets)
   ```toml
   BACKEND_URL = "https://dossier-q74p.onrender.com"
   ```

3. Deploy and get your live URL!

---

## 💬 Example Queries

| User Query | Generated Drive API Query |
|---|---|
| "find budget PDFs" | `(name contains 'budget') and mimeType = 'application/pdf' and trashed = false and mimeType != 'application/vnd.google-apps.folder'` |
| "reports from last week" | `(name contains 'reports' or name contains 'report') and modifiedTime > '2024-05-05T00:00:00' and trashed = false and mimeType != 'application/vnd.google-apps.folder'` |
| "documents mentioning quarterly revenue" | `fullText contains 'quarterly revenue' and trashed = false and mimeType != 'application/vnd.google-apps.folder'` |
| "show me all spreadsheets" | `(mimeType = 'application/vnd.google-apps.spreadsheet' or mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') and trashed = false and mimeType != 'application/vnd.google-apps.folder'` |
| "find invoices" | `(name contains 'invoices' or name contains 'invoice') and trashed = false and mimeType != 'application/vnd.google-apps.folder'` |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Backend Framework** | FastAPI + Uvicorn |
| **Agent Framework** | LangChain (Tool Calling Agent) |
| **LLM** | Groq API — `llama-3.3-70b-versatile` |
| **Drive Integration** | Google Drive API v3 (`files.list` method) |
| **Frontend** | Streamlit 1.39+ |
| **Backend Hosting** | Render (Web Service) |
| **Frontend Hosting** | Streamlit Cloud |
| **Language** | Python 3.11+ |

---

## 📁 Project Structure

```
dossier/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── agent_tool_based.py        # LangChain tool-calling agent
│   ├── drive_search_tool.py       # DriveSearchTool implementation
│   ├── drive_client.py            # Google Drive API wrapper
│   ├── schemas.py                 # Pydantic models
│   ├── requirements.txt           # Python dependencies
│   ├── runtime.txt                # Python version for Render
│   └── .env.example               # Environment variables template
│
├── frontend/
│   ├── app.py                     # Streamlit UI
│   ├── requirements.txt           # Frontend dependencies
│   └── .streamlit/
│       └── secrets.toml.example   # Secrets template
│
├── .gitignore
├── README.md
└── render.yaml                    # Render deployment config
```

---

## 🎯 How It Works

### 1. **User Input**
User types natural language query: *"Find budget reports from last week"*

### 2. **LLM Query Generation**
The LLM translates the request into a Drive API query string:
```
(name contains 'budget' or name contains 'report') 
and modifiedTime > '2024-05-05T00:00:00' 
and trashed = false 
and mimeType != 'application/vnd.google-apps.folder'
```

### 3. **Tool Execution**
`DriveSearchTool` executes the query via Google Drive API:
- Uses `files.list` method
- Searches recursively in subfolders
- Returns matching files with metadata

### 4. **Smart Retry**
If no results found, agent automatically:
- Broadens search criteria
- Removes date filters
- Tries again with relaxed query

### 5. **Response Formatting**
LLM generates friendly response:
*"I found 4 daily reports in PDF format. You can view them by clicking on the file cards."*

---

## 🔍 Search Capabilities

### Supported Search Types

✅ **Name Search** (partial match)
```
name contains 'invoice'
```

✅ **Content Search** (full-text)
```
fullText contains 'quarterly revenue'
```

✅ **File Type Filtering**
```
mimeType = 'application/pdf'
mimeType contains 'image/'
```

✅ **Date Filtering**
```
modifiedTime > '2024-01-01T00:00:00'
modifiedTime < '2024-12-31T23:59:59'
```

✅ **Complex Queries**
```
(name contains 'budget' or fullText contains 'budget') 
and mimeType = 'application/pdf' 
and modifiedTime > '2024-01-01T00:00:00'
```

### Supported File Types

- **Documents**: PDF, Google Docs, Word (.docx)
- **Spreadsheets**: Google Sheets, Excel (.xlsx)
- **Presentations**: Google Slides, PowerPoint (.pptx)
- **Images**: JPEG, PNG, GIF, WebP
- **And more**: Any file type supported by Google Drive

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- Built with [LangChain](https://www.langchain.com/)
- Powered by [Groq](https://groq.com/)
- Uses [Google Drive API](https://developers.google.com/drive)
- Frontend with [Streamlit](https://streamlit.io/)

---

**Made with ❤️ by Magenta91**
