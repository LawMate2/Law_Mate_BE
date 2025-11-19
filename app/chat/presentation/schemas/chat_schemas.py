from typing import List, Optional
from pydantic import BaseModel


class ChatMessageSchema(BaseModel):
    role: str
    content: str

class LawReferenceSchema(BaseModel):
    law_name: str
    article: Optional[str] = None
    summary: Optional[str] = None
    reference_url: Optional[str] = None
    provider: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    conversation_history: List[ChatMessageSchema] = []


class ChatResponse(BaseModel):
    response: str
    session_id: str
    conversation_history: List[ChatMessageSchema] = []
    related_laws: List[LawReferenceSchema] = []
    law_context: Optional[str] = None
