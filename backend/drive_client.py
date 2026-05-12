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
    """Execute a Drive API files.list query scoped to the designated folder and all subfolders."""
    service = get_drive_service()

    # Search recursively: don't restrict to immediate children
    # Instead, we'll get all files matching the query and filter by checking if they're descendants
    # For simplicity, we'll just search within the Drive without the parent restriction
    # and rely on the service account only having access to the shared folder
    
    full_query = f"({q_string}) and trashed = false"

    results = (
        service.files()
        .list(
            q=full_query,
            pageSize=max_results,
            fields="files(id, name, mimeType, webViewLink, modifiedTime, parents)",
            orderBy="modifiedTime desc",
            # Use corpora to search only in the user's drive (not shared drives)
            corpora="user",
        )
        .execute()
    )

    files = results.get("files", [])
    
    # If folder_id is provided, filter to only include files that are descendants of that folder
    if folder_id:
        files = filter_descendants(service, files, folder_id)
    
    return files


def filter_descendants(service, files: List[dict], root_folder_id: str) -> List[dict]:
    """Filter files to only include those that are descendants of the root folder."""
    descendants = []
    
    for file in files:
        if is_descendant(service, file.get("id"), root_folder_id):
            descendants.append(file)
    
    return descendants


def is_descendant(service, file_id: str, root_folder_id: str, max_depth: int = 10) -> bool:
    """Check if a file is a descendant of the root folder by traversing up the parent chain."""
    if not file_id:
        return False
    
    visited = set()
    current_id = file_id
    depth = 0
    
    while current_id and depth < max_depth:
        if current_id in visited:
            break
        visited.add(current_id)
        
        if current_id == root_folder_id:
            return True
        
        try:
            file_metadata = service.files().get(fileId=current_id, fields="parents").execute()
            parents = file_metadata.get("parents", [])
            
            if not parents:
                break
            
            # Check if root_folder_id is in the immediate parents
            if root_folder_id in parents:
                return True
            
            # Move up to the first parent
            current_id = parents[0]
            depth += 1
        except Exception:
            break
    
    return False
