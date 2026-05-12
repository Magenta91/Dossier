import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON env var not set")
    creds_dict = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


def search_files(q_string: str, folder_id: str, max_results: int = 15) -> List[dict]:
    """Execute a Drive API files.list query scoped to the designated folder."""
    service = get_drive_service()

    folder_clause = f"'{folder_id}' in parents"
    full_query = f"({q_string}) and {folder_clause} and trashed = false"

    results = (
        service.files()
        .list(
            q=full_query,
            pageSize=max_results,
            fields="files(id, name, mimeType, webViewLink, modifiedTime)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )

    return results.get("files", [])
