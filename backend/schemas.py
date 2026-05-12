from pydantic import BaseModel
from typing import Optional, List


class FileResult(BaseModel):
    id: str
    name: str
    mimeType: str
    webViewLink: str
    modifiedTime: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str
    files: List[FileResult] = []
    session_id: str
