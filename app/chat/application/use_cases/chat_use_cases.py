import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from app.chat.application.services.llm_service import LLMService
from app.chat.application.services.law_information_service import (
    LawInformationService,
    LawSearchResult,
)
from app.chat.domain.entities.chat_message import ChatMessage
from app.chat.domain.entities.chat_session import ChatSession
from app.chat.domain.entities.law_reference import LawReference
from app.chat.domain.repositories.chat_message_repository import ChatMessageRepository
from app.chat.domain.repositories.chat_session_repository import ChatSessionRepository
from app.search.application.use_cases.search_use_cases import SearchUseCases
from app.shared.services.mlflow_tracker import MLflowTracker


@dataclass
class ChatGenerationResult:
    """챗봇 응답 결과"""

    response: str
    related_laws: List[LawReference]
    law_context: str = ""


class ChatUseCases:
    """채팅 관련 유스케이스"""

    def __init__(
        self,
        chat_session_repository: ChatSessionRepository,
        chat_message_repository: ChatMessageRepository,
        search_use_cases: SearchUseCases,
        llm_service: LLMService,
        mlflow_tracker: MLflowTracker,
        law_information_service: LawInformationService
    ):
        self.chat_session_repository = chat_session_repository
        self.chat_message_repository = chat_message_repository
        self.search_use_cases = search_use_cases
        self.llm_service = llm_service
        self.mlflow_tracker = mlflow_tracker
        self.law_information_service = law_information_service

    async def start_chat_session(self, metadata: Dict[str, Any] = None) -> ChatSession:
        """새로운 채팅 세션 시작"""
        session = ChatSession.create_new(metadata)
        return await self.chat_session_repository.save(session)

    async def send_message(
        self,
        session_id: str,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> ChatGenerationResult:
        """메시지 전송 및 응답 생성"""
        start_time = time.time()

        with self.mlflow_tracker.start_run("chat_interaction"):
            try:
                # 세션 조회 또는 생성
                session = await self.chat_session_repository.find_by_session_id(session_id)
                if not session:
                    session = await self.start_chat_session({"created_from": "chat"})
                    session_id = session.session_id

                # 파라미터 로깅
                await self.mlflow_tracker.log_params({
                    "session_id": session_id,
                    "user_message": user_message,
                    "conversation_length": len(conversation_history) if conversation_history else 0
                })

                # 사용자 메시지 저장
                user_msg = ChatMessage.create_user_message(session_id, user_message)
                await self.chat_message_repository.save(user_msg)

                # 컨텍스트 검색
                search_start = time.time()
                search_result = await self.search_use_cases.search_documents(user_message)
                retrieve_time = time.time() - search_start

                law_search_result: LawSearchResult = await self.law_information_service.search_related_laws(
                    user_message
                )
                combined_context_segments: List[str] = []
                if search_result.combined_context:
                    combined_context_segments.append(search_result.combined_context)
                if law_search_result.context_block:
                    combined_context_segments.append(law_search_result.context_block)
                combined_context = "\n\n".join(segment.strip() for segment in combined_context_segments if segment)

                # LLM 응답 생성
                generate_start = time.time()
                response = await self.llm_service.generate_response(
                    query=user_message,
                    context=combined_context,
                    conversation_history=conversation_history or []
                )
                generate_time = time.time() - generate_start

                total_time = time.time() - start_time

                # 어시스턴트 메시지 생성 및 저장
                assistant_msg = ChatMessage.create_assistant_message(
                    session_id=session_id,
                    content=response,
                    retrieve_time=retrieve_time,
                    generate_time=generate_time,
                    total_time=total_time,
                    context_length=len(combined_context),
                    similarity_scores=search_result.similarity_scores,
                    retrieved_chunks=search_result.retrieved_chunks
                )

                if law_search_result.references:
                    assistant_msg.metadata["related_laws"] = [
                        asdict(reference) for reference in law_search_result.references
                    ]

                await self.chat_message_repository.save(assistant_msg)

                # 세션 업데이트
                session.increment_message_count()
                await self.chat_session_repository.save(session)

                # 메트릭 로깅
                await self.mlflow_tracker.log_metrics({
                    "retrieve_time": retrieve_time,
                    "generate_time": generate_time,
                    "total_time": total_time,
                    "context_length": len(combined_context),
                    "response_length": len(response),
                    "max_similarity_score": search_result.max_similarity_score,
                    "avg_similarity_score": search_result.avg_similarity_score,
                    "related_law_count": len(law_search_result.references),
                    "success": 1
                })

                return ChatGenerationResult(
                    response=response,
                    related_laws=law_search_result.references,
                    law_context=law_search_result.context_block
                )

            except Exception as e:
                await self.mlflow_tracker.log_metric("success", 0)
                await self.mlflow_tracker.log_text(str(e), "error.txt")
                raise

    async def get_chat_history(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChatMessage]:
        """채팅 히스토리 조회"""
        return await self.chat_message_repository.find_by_session_id(session_id, skip, limit)

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """채팅 세션 조회"""
        return await self.chat_session_repository.find_by_session_id(session_id)

    async def list_sessions(self, skip: int = 0, limit: int = 100) -> List[ChatSession]:
        """채팅 세션 목록 조회"""
        return await self.chat_session_repository.find_all(skip, limit)

    async def delete_session(self, session_id: str) -> bool:
        """채팅 세션 삭제"""
        session = await self.chat_session_repository.find_by_session_id(session_id)
        if not session:
            return False

        return await self.chat_session_repository.delete(session.id)

    async def get_chat_statistics(self) -> dict:
        """채팅 통계"""
        total_sessions = await self.chat_session_repository.count()
        total_messages = await self.chat_message_repository.count()

        # 최근 메시지 성능 분석
        recent_messages = await self.chat_message_repository.find_recent_assistant_messages(100)

        avg_response_time = 0.0
        avg_retrieve_time = 0.0
        avg_generate_time = 0.0

        if recent_messages:
            total_response_times = [msg.total_time for msg in recent_messages if msg.total_time > 0]
            total_retrieve_times = [msg.retrieve_time for msg in recent_messages if msg.retrieve_time > 0]
            total_generate_times = [msg.generate_time for msg in recent_messages if msg.generate_time > 0]

            if total_response_times:
                avg_response_time = sum(total_response_times) / len(total_response_times)
            if total_retrieve_times:
                avg_retrieve_time = sum(total_retrieve_times) / len(total_retrieve_times)
            if total_generate_times:
                avg_generate_time = sum(total_generate_times) / len(total_generate_times)

        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
            "avg_response_time": avg_response_time,
            "avg_retrieve_time": avg_retrieve_time,
            "avg_generate_time": avg_generate_time
        }
