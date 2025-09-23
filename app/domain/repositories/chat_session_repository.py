from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.chat_session import ChatSession


class ChatSessionRepository(ABC):
    """채팅 세션 저장소 인터페이스"""

    @abstractmethod
    async def save(self, session: ChatSession) -> ChatSession:
        """세션 저장"""
        pass

    @abstractmethod
    async def find_by_id(self, session_id: int) -> Optional[ChatSession]:
        """ID로 세션 조회"""
        pass

    @abstractmethod
    async def find_by_session_id(self, session_id: str) -> Optional[ChatSession]:
        """세션 ID로 조회"""
        pass

    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> List[ChatSession]:
        """모든 세션 조회"""
        pass

    @abstractmethod
    async def delete(self, session_id: int) -> bool:
        """세션 삭제"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """세션 총 개수"""
        pass

    @abstractmethod
    async def update_message_count(self, session_id: str, message_count: int):
        """메시지 수 업데이트"""
        pass