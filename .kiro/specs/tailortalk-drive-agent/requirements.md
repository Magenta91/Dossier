# Requirements Document

## Introduction

TailorTalk is a conversational AI agent that enables users to find files in a designated
Google Drive folder using plain English. It must handle multi-turn conversations, search
by multiple criteria (name, type, content, date), and gracefully recover when searches
return zero results.

---

## Requirements

### Requirement 1: Natural Language File Search

**User Story:** As a user, I want to describe a file in plain English, so that I can find
it in Google Drive without knowing Drive's query syntax.

#### Acceptance Criteria

1. WHEN a user sends a message describing a file by name
   THE SYSTEM SHALL extract the name and search Google Drive using a `name contains` query.

2. WHEN a user mentions a file type (e.g. "PDF", "spreadsheet", "image")
   THE SYSTEM SHALL map it to the correct Google Drive `mimeType` and include it in the query.

3. WHEN a user describes content inside a file (e.g. "document about revenue")
   THE SYSTEM SHALL use `fullText contains` in the Drive query.

4. WHEN a user specifies a time range (e.g. "from last month", "modified this week")
   THE SYSTEM SHALL resolve the relative date to ISO format and apply `modifiedTime` filters.

5. WHEN a user combines multiple criteria (e.g. "budget PDF from last month")
   THE SYSTEM SHALL AND-chain all applicable filters into a single Drive API `q` string.

---

### Requirement 2: Fallback Query Relaxation

**User Story:** As a user, I want the agent to try harder when it finds nothing, so that
I still get useful results even if my query was too specific.

#### Acceptance Criteria

1. WHEN a Drive search returns zero results
   THE SYSTEM SHALL automatically retry with a relaxed query (dropping date filters first).

2. WHEN a second retry also returns zero results
   THE SYSTEM SHALL retry again dropping both date and file type filters.

3. WHEN a third retry also returns zero results
   THE SYSTEM SHALL inform the user that nothing was found and suggest alternative searches.

4. WHEN any retry attempt returns results
   THE SYSTEM SHALL stop retrying and return those results immediately.

---

### Requirement 3: Conversational Memory

**User Story:** As a user, I want the agent to remember what I asked before, so that I can
refine my search with follow-up messages.

#### Acceptance Criteria

1. WHEN a user sends a follow-up message referencing prior results (e.g. "only PDFs of those")
   THE SYSTEM SHALL combine the new constraint with the previous search intent.

2. WHEN a user starts a new session
   THE SYSTEM SHALL have no memory of previous sessions.

3. WHEN a conversation exceeds 20 messages
   THE SYSTEM SHALL retain only the most recent 20 messages to prevent context overflow.

---

### Requirement 4: File Result Presentation

**User Story:** As a user, I want to see found files as interactive cards, so that I can
open them directly in Google Drive from the chat.

#### Acceptance Criteria

1. WHEN files are found
   THE SYSTEM SHALL display each file as a card showing: icon, name, file type label, and last modified date.

2. WHEN a file card is displayed
   THE SYSTEM SHALL include a clickable "Open ↗" button linking to the file's `webViewLink` in Google Drive.

3. WHEN zero files are found after all retries
   THE SYSTEM SHALL display a friendly message with no file cards and suggest alternative search terms.

4. WHEN results are returned
   THE SYSTEM SHALL show a natural language summary (2–3 sentences) above the file cards.

---

### Requirement 5: Session Management

**User Story:** As a user, I want to be able to clear my chat history, so that I can start
a fresh search without leftover context.

#### Acceptance Criteria

1. WHEN a user clicks "Clear conversation" in the sidebar
   THE SYSTEM SHALL reset the chat history and generate a new session ID.

2. WHEN the page first loads
   THE SYSTEM SHALL show suggested query buttons to help the user get started.

3. WHEN a suggested query button is clicked
   THE SYSTEM SHALL submit it as a chat message automatically.

---

### Requirement 6: API Contract

**User Story:** As the frontend, I want a stable JSON API, so that the Streamlit app can
communicate with the FastAPI backend reliably.

#### Acceptance Criteria

1. WHEN the frontend POSTs `{"message": string, "session_id": string}` to `/chat`
   THE SYSTEM SHALL respond with `{"response": string, "files": FileResult[], "session_id": string}`.

2. WHEN the backend is healthy
   THE SYSTEM SHALL return `{"status": "ok"}` from `GET /health`.

3. WHEN a request times out or the backend is unavailable
   THE SYSTEM SHALL display a user-friendly error message in the Streamlit UI.

4. WHEN the backend is deployed on Render
   THE SYSTEM SHALL accept CORS requests from any origin.
