from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


@dataclass
class ChatSession:
    """채팅 세션 도메인 엔티티"""
    session_id: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    total_messages: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def create_new(cls, metadata: Dict[str, Any] = None) -> "ChatSession":
        """새로운 채팅 세션 생성"""
        return cls(
            session_id=str(uuid.uuid4()),
            created_at=datetime.now(),
            metadata=metadata or {}
        )

    def increment_message_count(self):
        """메시지 수 증가"""
        self.total_messages += 1
        self.updated_at = datetime.now()

    def update_last_activity(self):
        """마지막 활동 시간 업데이트"""
        self.updated_at = datetime.now()