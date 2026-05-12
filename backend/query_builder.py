from typing import Optional

# Maps human-readable type names → Drive mimeType strings
MIME_TYPE_MAP = {
    "pdf": "application/pdf",
    "doc": "application/vnd.google-apps.document",
    "gdoc": "application/vnd.google-apps.document",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "sheet": "application/vnd.google-apps.spreadsheet",
    "sheets": "application/vnd.google-apps.spreadsheet",
    "gsheet": "application/vnd.google-apps.spreadsheet",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image": "image/",          # prefix match
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "presentation": "application/vnd.google-apps.presentation",
    "slides": "application/vnd.google-apps.presentation",
    "gslides": "application/vnd.google-apps.presentation",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def build_query(
    name: Optional[str] = None,
    file_type: Optional[str] = None,
    content_query: Optional[str] = None,
    date_after: Optional[str] = None,
    date_before: Optional[str] = None,
    relax_level: int = 0,
) -> str:
    """
    Build a Google Drive API `q` parameter string from structured intent.

    Relaxation levels control how strict the search is — used by the
    fallback loop when zero results are returned:
      Level 0  →  Full query (name + type + date + content)
      Level 1  →  Drop date filters
      Level 2  →  Drop date AND type filters
      Level 3  →  Name or content only (broadest possible)

    Returns a valid Drive API q string.
    """
    parts = []

    # ── Name filter ──────────────────────────────────────────────────────────
    if name:
        # Escape single quotes in the name to avoid breaking the query
        safe_name = name.replace("'", "\\'")
        parts.append(f"name contains '{safe_name}'")

    # ── File type filter (dropped at relax level >= 2) ───────────────────────
    if file_type and relax_level < 2:
        mime = MIME_TYPE_MAP.get(file_type.lower())
        if mime:
            if mime.endswith("/"):
                # Prefix match (e.g. "image/" covers all image types)
                parts.append(f"mimeType contains '{mime}'")
            else:
                parts.append(f"mimeType = '{mime}'")

    # ── Date filters (dropped at relax level >= 1) ────────────────────────────
    if relax_level < 1:
        if date_after:
            parts.append(f"modifiedTime > '{date_after}T00:00:00'")
        if date_before:
            parts.append(f"modifiedTime < '{date_before}T23:59:59'")

    # ── Full-text search ──────────────────────────────────────────────────────
    if content_query:
        safe_content = content_query.replace("'", "\\'")
        parts.append(f"fullText contains '{safe_content}'")

    # ── Default: return everything in the folder ──────────────────────────────
    if not parts:
        return "trashed = false"

    return " and ".join(parts)
