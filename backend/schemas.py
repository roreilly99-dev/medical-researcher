from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    upload_date: datetime
    status: str
    markdown_content: Optional[str] = None
    extracted_data: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    images: Optional[list[str]] = None

    model_config = {"from_attributes": True}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[ChatMessage] = []


class ChatSource(BaseModel):
    document_id: str
    filename: str
    content: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = []
