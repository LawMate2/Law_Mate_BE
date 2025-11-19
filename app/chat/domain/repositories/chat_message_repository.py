from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.chat_message import ChatMessage


class ChatMessageRepository(ABC):
    """채팅 메시지 저장소 인터페이스"""

    @abstractmethod
    async def save(self, message: ChatMessage) -> ChatMessage:
        """메시지 저장"""
        pass

    @abstractmethod
    async def find_by_id(self, message_id: int) -> Optional[ChatMessage]:
        """ID로 메시지 조회"""
        pass

    @abstractmethod
    async def find_by_session_id(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        """세션 ID로 메시지들 조회"""
        pass

    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> List[ChatMessage]:
        """모든 메시지 조회"""
        pass

    @abstractmethod
    async def delete(self, message_id: int) -> bool:
        """메시지 삭제"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """메시지 총 개수"""
        pass

    @abstractmethod
    async def count_by_session(self, session_id: str) -> int:
        """세션별 메시지 개수"""
        pass

    @abstractmethod
    async def find_recent_assistant_messages(self, limit: int = 100) -> List[ChatMessage]:
        """최근 어시스턴트 메시지들 조회"""
        pass