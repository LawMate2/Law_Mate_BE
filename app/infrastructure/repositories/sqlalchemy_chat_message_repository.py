from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...domain.entities.chat_message import ChatMessage, MessageRole
from ...domain.repositories.chat_message_repository import ChatMessageRepository
from ...db.models import ChatMessage as ChatMessageModel


class SqlAlchemyChatMessageRepository(ChatMessageRepository):
    """SQLAlchemy를 사용한 채팅 메시지 저장소 구현"""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def save(self, message: ChatMessage) -> ChatMessage:
        """메시지 저장"""
        db_message = ChatMessageModel(
            session_id=message.session_id,
            role=message.role.value,
            content=message.content,
            timestamp=message.timestamp,
            retrieve_time=message.retrieve_time,
            generate_time=message.generate_time,
            total_time=message.total_time,
            context_length=message.context_length,
            response_length=message.response_length,
            similarity_scores=message.similarity_scores,
            retrieved_chunks=message.retrieved_chunks,
            metadata=message.metadata
        )

        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)

        message.id = db_message.id
        return message

    async def find_by_id(self, message_id: int) -> Optional[ChatMessage]:
        """ID로 메시지 조회"""
        db_message = self.db.query(ChatMessageModel).filter(
            ChatMessageModel.id == message_id
        ).first()

        if db_message:
            return self._to_domain_entity(db_message)
        return None

    async def find_by_session_id(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        """세션 ID로 메시지들 조회"""
        db_messages = self.db.query(ChatMessageModel).filter(
            ChatMessageModel.session_id == session_id
        ).order_by(ChatMessageModel.timestamp).offset(skip).limit(limit).all()

        return [self._to_domain_entity(msg) for msg in db_messages]

    async def find_all(self, skip: int = 0, limit: int = 100) -> List[ChatMessage]:
        """모든 메시지 조회"""
        db_messages = self.db.query(ChatMessageModel).offset(skip).limit(limit).all()
        return [self._to_domain_entity(msg) for msg in db_messages]

    async def delete(self, message_id: int) -> bool:
        """메시지 삭제"""
        db_message = self.db.query(ChatMessageModel).filter(
            ChatMessageModel.id == message_id
        ).first()

        if db_message:
            self.db.delete(db_message)
            self.db.commit()
            return True
        return False

    async def count(self) -> int:
        """메시지 총 개수"""
        return self.db.query(ChatMessageModel).count()

    async def count_by_session(self, session_id: str) -> int:
        """세션별 메시지 개수"""
        return self.db.query(ChatMessageModel).filter(
            ChatMessageModel.session_id == session_id
        ).count()

    async def find_recent_assistant_messages(self, limit: int = 100) -> List[ChatMessage]:
        """최근 어시스턴트 메시지들 조회"""
        db_messages = self.db.query(ChatMessageModel).filter(
            ChatMessageModel.role == MessageRole.ASSISTANT.value
        ).order_by(desc(ChatMessageModel.timestamp)).limit(limit).all()

        return [self._to_domain_entity(msg) for msg in db_messages]

    def _to_domain_entity(self, db_message: ChatMessageModel) -> ChatMessage:
        """DB 모델을 도메인 엔티티로 변환"""
        return ChatMessage(
            id=db_message.id,
            session_id=db_message.session_id,
            role=MessageRole(db_message.role),
            content=db_message.content,
            timestamp=db_message.timestamp,
            retrieve_time=db_message.retrieve_time or 0.0,
            generate_time=db_message.generate_time or 0.0,
            total_time=db_message.total_time or 0.0,
            context_length=db_message.context_length or 0,
            response_length=db_message.response_length or 0,
            similarity_scores=db_message.similarity_scores or [],
            retrieved_chunks=db_message.retrieved_chunks or 0,
            metadata=db_message.metadata or {}
        )