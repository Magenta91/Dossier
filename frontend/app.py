import streamlit as st
import requests
import uuid
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

MIME_ICONS = {
    "application/pdf": "📄",
    "application/vnd.google-apps.document": "📝",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "📝",
    "application/vnd.google-apps.spreadsheet": "📊",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "📊",
    "application/vnd.google-apps.presentation": "📑",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "📑",
    "image/jpeg": "🖼️",
    "image/png": "🖼️",
    "image/gif": "🖼️",
    "image/webp": "🖼️",
}

MIME_LABELS = {
    "application/pdf": "PDF",
    "application/vnd.google-apps.document": "Google Doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word Doc",
    "application/vnd.google-apps.spreadsheet": "Google Sheet",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
    "application/vnd.google-apps.presentation": "Google Slides",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PowerPoint",
    "image/jpeg": "Image",
    "image/png": "Image",
}

SUGGESTED_QUERIES = [
    "Show me all PDFs",
    "Find files modified this week",
    "Search for documents about revenue",
    "List all spreadsheets",
    "Find images",
]


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_icon(mime: str) -> str:
    return MIME_ICONS.get(mime, "📁")


def get_label(mime: str) -> str:
    return MIME_LABELS.get(mime, "File")


def format_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso


def render_file_card(file: dict):
    icon = get_icon(file["mimeType"])
    label = get_label(file["mimeType"])
    modified = format_date(file["modifiedTime"]) if file.get("modifiedTime") else ""

    with st.container():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"**{icon} {file['name']}**")
            st.caption(f"{label}{'  ·  ' + modified if modified else ''}")
        with col2:
            if file.get("webViewLink"):
                st.link_button("Open ↗", file["webViewLink"], use_container_width=True)
        st.divider()


def call_backend(message: str, session_id: str) -> dict:
    response = requests.post(
        f"{BACKEND_URL}/chat",
        json={"message": message, "session_id": session_id},
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


# ── Page setup ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dossier",
    page_icon="🗂️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .main-header { text-align: center; padding: 1.5rem 0 0.5rem; }
    .main-header h1 { font-size: 2rem; margin-bottom: 0.2rem; }
    .main-header p { color: #888; font-size: 0.95rem; }
    .stDivider { margin: 0.4rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ──────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="main-header">
        <h1>🗂️ Dossier</h1>
        <p>Your AI-powered Google Drive assistant</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Suggested queries (shown only when chat is empty) ─────────────────────────
if not st.session_state.messages:
    st.markdown("#### Try asking:")
    cols = st.columns(len(SUGGESTED_QUERIES))
    for i, suggestion in enumerate(SUGGESTED_QUERIES):
        if cols[i].button(suggestion, use_container_width=True, key=f"sug_{i}"):
            st.session_state.pending_message = suggestion
            st.rerun()

st.markdown("---")

# ── Render conversation history ────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("files"):
            st.markdown(f"**{len(msg['files'])} file(s) found:**")
            for file in msg["files"]:
                render_file_card(file)

# ── Handle suggested query click ──────────────────────────────────────────────
pending = st.session_state.pop("pending_message", None)

# ── Chat input ─────────────────────────────────────────────────────────────────
prompt = st.chat_input("Search your Drive... (e.g. 'find budget PDFs from last month')")

if prompt or pending:
    user_input = prompt or pending

    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call backend and show response
    with st.chat_message("assistant"):
        with st.spinner("Searching your Drive..."):
            try:
                data = call_backend(user_input, st.session_state.session_id)

                response_text = data.get("response", "")
                files = data.get("files", [])

                st.markdown(response_text)

                if files:
                    st.markdown(f"**{len(files)} file(s) found:**")
                    for file in files:
                        render_file_card(file)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response_text,
                        "files": files,
                    }
                )

            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. The backend may be starting up — please try again.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Could not connect to the backend. Make sure it's running.")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")

# ── Sidebar: session controls ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Session")
    st.caption(f"ID: `{st.session_state.session_id[:8]}...`")

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        "Dossier uses a LangGraph agent with a fallback query relaxation loop "
        "to find files in Google Drive via natural language."
    )
