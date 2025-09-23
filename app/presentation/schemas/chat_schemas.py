from typing import List, Optional
from pydantic import BaseModel


class ChatMessageSchema(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    conversation_history: List[ChatMessageSchema] = []


class ChatResponse(BaseModel):
    response: str
    session_id: str
    conversation_history: List[ChatMessageSchema] = []