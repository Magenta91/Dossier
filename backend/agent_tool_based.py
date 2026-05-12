"""
Tool-based agent: LLM generates Drive API queries directly using function calling.
"""
import os
from datetime import datetime
from typing import List
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage
from drive_search_tool import DriveSearchTool

# ── LLM setup ────────────────────────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

# ── Tools ────────────────────────────────────────────────────────────────────
tools = [DriveSearchTool()]

# ── Agent Prompt ─────────────────────────────────────────────────────────────
today = datetime.now().strftime("%Y-%m-%d")

prompt = ChatPromptTemplate.from_messages([
    ("system", f"""You are Dossier, an AI assistant that helps users search Google Drive using natural language.

Today's date: {today}

Your job:
1. Understand the user's search request
2. Translate it into a properly formatted Google Drive API 'q' parameter string
3. Use the search_google_drive tool with that query string
4. Present the results in a friendly, conversational way

Google Drive Query Syntax:
- name contains 'keyword' — search in filename (case-insensitive substring match)
- fullText contains 'keyword' — search inside file content
- mimeType = 'type' — filter by file type
  - PDF: application/pdf
  - Google Doc: application/vnd.google-apps.document
  - Word: application/vnd.openxmlformats-officedocument.wordprocessingml.document
  - Google Sheet: application/vnd.google-apps.spreadsheet
  - Excel: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
  - Image: image/jpeg, image/png, or use 'mimeType contains "image/"'
- modifiedTime > 'YYYY-MM-DDTHH:MM:SS' — files modified after date
- modifiedTime < 'YYYY-MM-DDTHH:MM:SS' — files modified before date
- Combine conditions with 'and' or 'or'
- Use parentheses for grouping: (condition1 or condition2) and condition3

IMPORTANT Rules:
- ALWAYS include: trashed = false
- ALWAYS exclude folders: mimeType != 'application/vnd.google-apps.folder'
- For plural searches (e.g., "reports"), search for both singular and plural:
  (name contains 'reports' or name contains 'report')
- Resolve relative dates using today's date ({today})
- Use single quotes around string values in queries

Examples:
User: "Find the financial report from last week"
Query: (name contains 'financial' or name contains 'report') and modifiedTime > '{(datetime.now().replace(day=datetime.now().day-7)).strftime("%Y-%m-%d")}T00:00:00' and trashed = false and mimeType != 'application/vnd.google-apps.folder'

User: "Show me all PDFs"
Query: mimeType = 'application/pdf' and trashed = false and mimeType != 'application/vnd.google-apps.folder'

User: "Find invoices"
Query: (name contains 'invoices' or name contains 'invoice') and trashed = false and mimeType != 'application/vnd.google-apps.folder'

User: "Documents that mention quarterly revenue"
Query: fullText contains 'quarterly revenue' and trashed = false and mimeType != 'application/vnd.google-apps.folder'

After getting results:
- If files found: briefly describe what was found, the UI will show file cards
- If no files found: suggest alternative searches or broader criteria
- Keep responses conversational and helpful
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# ── Create Agent ─────────────────────────────────────────────────────────────
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=3,
    return_intermediate_steps=True,  # CRITICAL: Return tool outputs
)


def run_agent(message: str, chat_history: List = None) -> dict:
    """
    Run the tool-based agent with the user's message.
    
    Args:
        message: User's natural language query
        chat_history: List of previous messages (LangChain message objects)
    
    Returns:
        dict with 'response' (str) and 'files' (list)
    """
    if chat_history is None:
        chat_history = []
    
    try:
        result = agent_executor.invoke({
            "input": message,
            "chat_history": chat_history,
        })
        
        # Extract the response text
        response_text = result.get("output", "I couldn't process that request.")
        
        # Extract files from ALL intermediate steps (tool outputs)
        # Collect files from ALL successful tool calls
        all_files = []
        intermediate_steps = result.get("intermediate_steps", [])
        
        print(f"DEBUG: Found {len(intermediate_steps)} intermediate steps")
        
        for i, (action, observation) in enumerate(intermediate_steps):
            print(f"DEBUG: Step {i}: observation type = {type(observation)}")
            if isinstance(observation, dict):
                print(f"DEBUG: Step {i}: observation keys = {observation.keys()}")
                if observation.get("success") and observation.get("files"):
                    step_files = observation.get("files", [])
                    print(f"DEBUG: Step {i}: Found {len(step_files)} files")
                    # Add files from this step (avoid duplicates by ID)
                    existing_ids = {f.get("id") for f in all_files}
                    for file in step_files:
                        if file.get("id") not in existing_ids:
                            all_files.append(file)
        
        print(f"DEBUG: Final files count = {len(all_files)}")
        
        return {
            "response": response_text,
            "files": all_files,
        }
        
    except Exception as e:
        print(f"DEBUG: Exception in run_agent: {e}")
        return {
            "response": f"Sorry, I encountered an error: {str(e)}",
            "files": [],
        }
