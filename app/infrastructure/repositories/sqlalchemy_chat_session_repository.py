from typing import List, Optional
from sqlalchemy.orm import Session

from ...domain.entities.chat_session import ChatSession
from ...domain.repositories.chat_session_repository import ChatSessionRepository
from ...db.models import ChatSession as ChatSessionModel


class SqlAlchemyChatSessionRepository(ChatSessionRepository):
    """SQLAlchemy를 사용한 채팅 세션 저장소 구현"""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def save(self, session: ChatSession) -> ChatSession:
        """세션 저장"""
        if session.id is None:
            # 새 세션 생성
            db_session = ChatSessionModel(
                session_id=session.session_id,
                created_at=session.created_at,
                updated_at=session.updated_at,
                total_messages=session.total_messages,
                metadata=session.metadata
            )
            self.db.add(db_session)
            self.db.commit()
            self.db.refresh(db_session)
            session.id = db_session.id
        else:
            # 기존 세션 업데이트
            db_session = self.db.query(ChatSessionModel).filter(
                ChatSessionModel.id == session.id
            ).first()
            if db_session:
                db_session.updated_at = session.updated_at
                db_session.total_messages = session.total_messages
                db_session.metadata = session.metadata
                self.db.commit()

        return session

    async def find_by_id(self, session_id: int) -> Optional[ChatSession]:
        """ID로 세션 조회"""
        db_session = self.db.query(ChatSessionModel).filter(
            ChatSessionModel.id == session_id
        ).first()

        if db_session:
            return self._to_domain_entity(db_session)
        return None

    async def find_by_session_id(self, session_id: str) -> Optional[ChatSession]:
        """세션 ID로 조회"""
        db_session = self.db.query(ChatSessionModel).filter(
            ChatSessionModel.session_id == session_id
        ).first()

        if db_session:
            return self._to_domain_entity(db_session)
        return None

    async def find_all(self, skip: int = 0, limit: int = 100) -> List[ChatSession]:
        """모든 세션 조회"""
        db_sessions = self.db.query(ChatSessionModel).offset(skip).limit(limit).all()
        return [self._to_domain_entity(session) for session in db_sessions]

    async def delete(self, session_id: int) -> bool:
        """세션 삭제"""
        db_session = self.db.query(ChatSessionModel).filter(
            ChatSessionModel.id == session_id
        ).first()

        if db_session:
            self.db.delete(db_session)
            self.db.commit()
            return True
        return False

    async def count(self) -> int:
        """세션 총 개수"""
        return self.db.query(ChatSessionModel).count()

    async def update_message_count(self, session_id: str, message_count: int):
        """메시지 수 업데이트"""
        db_session = self.db.query(ChatSessionModel).filter(
            ChatSessionModel.session_id == session_id
        ).first()

        if db_session:
            db_session.total_messages = message_count
            self.db.commit()

    def _to_domain_entity(self, db_session: ChatSessionModel) -> ChatSession:
        """DB 모델을 도메인 엔티티로 변환"""
        return ChatSession(
            id=db_session.id,
            session_id=db_session.session_id,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            total_messages=db_session.total_messages,
            metadata=db_session.metadata or {}
        )