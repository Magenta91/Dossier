"""
DriveSearchTool: A LangChain tool that executes Google Drive searches.
The LLM generates the Drive API q parameter string directly.
"""
import os
from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from drive_client import search_files


class DriveSearchInput(BaseModel):
    """Input schema for the Drive search tool."""
    q: str = Field(
        description=(
            "Google Drive API query string. Use Drive API syntax:\n"
            "- name contains 'keyword' — search filename\n"
            "- fullText contains 'keyword' — search file content\n"
            "- mimeType = 'application/pdf' — filter by type\n"
            "- modifiedTime > '2023-10-24T12:00:00' — date filters\n"
            "- Combine with 'and' / 'or'\n"
            "- Always exclude folders: mimeType != 'application/vnd.google-apps.folder'\n"
            "- Always exclude trash: trashed = false\n"
            "Example: name contains 'report' and mimeType = 'application/pdf' and modifiedTime > '2024-01-01T00:00:00'"
        )
    )


class DriveSearchTool(BaseTool):
    """Tool for searching Google Drive using natural language converted to Drive API queries."""
    
    name: str = "search_google_drive"
    description: str = (
        "Search for files in Google Drive. "
        "Input should be a properly formatted Google Drive API 'q' parameter string. "
        "Use Drive query syntax to search by name, content, type, and date. "
        "Returns a list of matching files with their metadata."
    )
    args_schema: Type[BaseModel] = DriveSearchInput
    
    def _run(self, q: str) -> dict:
        """Execute the Drive search and return results as structured data."""
        folder_id = os.getenv("DRIVE_FOLDER_ID", "")
        
        try:
            results = search_files(q, folder_id=folder_id, max_results=15)
            
            # Return structured data that can be used by both LLM and API
            return {
                "success": True,
                "count": len(results),
                "files": results,
                "query": q,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "count": 0,
                "files": [],
                "query": q,
            }
    
    async def _arun(self, q: str) -> dict:
        """Async version (not implemented, falls back to sync)."""
        return self._run(q)
