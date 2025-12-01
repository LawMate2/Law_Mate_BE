from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    role: str
    content: str
    id: Optional[str] = None


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


class ChatSessionSchema(BaseModel):
    """채팅 세션 스키마"""
    id: str = Field(..., description="세션 ID (session_id)")
    title: str = Field(..., description="채팅 제목")
    messages: List[ChatMessageSchema] = Field(default=[], description="메시지 목록")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChatHistoryResponse(BaseModel):
    """채팅 히스토리 응답"""
    chats: List[ChatSessionSchema] = Field(..., description="채팅 세션 목록")
    total: int = Field(..., description="전체 채팅 수")
