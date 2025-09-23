from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    """채팅 메시지 도메인 엔티티"""
    session_id: str
    role: MessageRole
    content: str
    id: Optional[int] = None
    timestamp: Optional[datetime] = None

    # 성능 메트릭
    retrieve_time: float = 0.0
    generate_time: float = 0.0
    total_time: float = 0.0
    context_length: int = 0
    response_length: int = 0

    # 검색 관련
    similarity_scores: List[float] = None
    retrieved_chunks: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.similarity_scores is None:
            self.similarity_scores = []
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def create_user_message(cls, session_id: str, content: str) -> "ChatMessage":
        """사용자 메시지 생성"""
        return cls(
            session_id=session_id,
            role=MessageRole.USER,
            content=content
        )

    @classmethod
    def create_assistant_message(
        cls,
        session_id: str,
        content: str,
        retrieve_time: float = 0.0,
        generate_time: float = 0.0,
        total_time: float = 0.0,
        context_length: int = 0,
        similarity_scores: List[float] = None,
        retrieved_chunks: int = 0
    ) -> "ChatMessage":
        """어시스턴트 메시지 생성"""
        return cls(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content,
            retrieve_time=retrieve_time,
            generate_time=generate_time,
            total_time=total_time,
            context_length=context_length,
            response_length=len(content),
            similarity_scores=similarity_scores or [],
            retrieved_chunks=retrieved_chunks
        )

    @property
    def is_user_message(self) -> bool:
        return self.role == MessageRole.USER

    @property
    def is_assistant_message(self) -> bool:
        return self.role == MessageRole.ASSISTANT