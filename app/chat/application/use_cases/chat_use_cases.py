import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from app.chat.application.services.rag_pipeline import LangGraphRAGPipeline
from app.chat.application.services.chat_cache_service import ChatCacheService
from app.chat.domain.entities.chat_message import ChatMessage
from app.chat.domain.entities.chat_session import ChatSession
from app.chat.domain.entities.law_reference import LawReference
from app.chat.domain.repositories.chat_message_repository import ChatMessageRepository
from app.chat.domain.repositories.chat_session_repository import ChatSessionRepository
from app.shared.services.mlflow_tracker import MLflowTracker


@dataclass
class ChatGenerationResult:
    """챗봇 응답 결과"""

    response: str
    related_laws: List[LawReference]
    law_context: str = ""
    session_id: str = ""


@dataclass
class UserChatHistory:
    """사용자 채팅 히스토리"""
    sessions: List[ChatSession]
    messages_by_session: Dict[str, List[ChatMessage]]


class ChatUseCases:
    """채팅 관련 유스케이스"""

    def __init__(
        self,
        chat_session_repository: ChatSessionRepository,
        chat_message_repository: ChatMessageRepository,
        rag_pipeline: LangGraphRAGPipeline,
        mlflow_tracker: MLflowTracker,
        chat_cache_service: ChatCacheService = None,
    ):
        self.chat_session_repository = chat_session_repository
        self.chat_message_repository = chat_message_repository
        self.rag_pipeline = rag_pipeline
        self.mlflow_tracker = mlflow_tracker
        self.chat_cache_service = chat_cache_service

    async def start_chat_session(
        self,
        user_id: int = None,
        title: str = None,
        metadata: Dict[str, Any] = None
    ) -> ChatSession:
        """새로운 채팅 세션 시작"""
        session = ChatSession.create_new(
            user_id=user_id,
            title=title,
            metadata=metadata
        )
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
                    session = await self.start_chat_session(
                        metadata={"created_from": "chat"}
                    )
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

                # LangGraph RAG 파이프라인 실행
                rag_start = time.time()
                rag_result = await self.rag_pipeline.arun(
                    query=user_message,
                    conversation_history=conversation_history or []
                )
                rag_elapsed = time.time() - rag_start
                retrieve_time = rag_result.retrieval_time
                generate_time = max(rag_elapsed - retrieve_time, 0.0)

                total_time = time.time() - start_time

                # 어시스턴트 메시지 생성 및 저장
                assistant_msg = ChatMessage.create_assistant_message(
                    session_id=session_id,
                    content=rag_result.response,
                    retrieve_time=retrieve_time,
                    generate_time=generate_time,
                    total_time=total_time,
                    context_length=len(rag_result.combined_context),
                    similarity_scores=rag_result.similarity_scores,
                    retrieved_chunks=rag_result.retrieved_chunks
                )

                if rag_result.law_references:
                    assistant_msg.metadata["related_laws"] = [
                        asdict(reference) for reference in rag_result.law_references
                    ]

                await self.chat_message_repository.save(assistant_msg)

                # 세션 업데이트
                session.increment_message_count()
                await self.chat_session_repository.save(session)

                # 메트릭 로깅
                await self.mlflow_tracker.log_metrics({
                    "retrieve_time": retrieve_time,
                    "embedding_time": rag_result.embedding_time,
                    "generate_time": generate_time,
                    "total_time": total_time,
                    "context_length": len(rag_result.combined_context),
                    "response_length": len(rag_result.response),
                    "max_similarity_score": max(rag_result.similarity_scores) if rag_result.similarity_scores else 0.0,
                    "avg_similarity_score": sum(rag_result.similarity_scores) / len(rag_result.similarity_scores) if rag_result.similarity_scores else 0.0,
                    "related_law_count": len(rag_result.law_references),
                    "success": 1
                })

                return ChatGenerationResult(
                    response=rag_result.response,
                    related_laws=rag_result.law_references,
                    law_context=rag_result.law_context,
                    session_id=session_id
                )

            except Exception as e:
                await self.mlflow_tracker.log_metric("success", 0)
                await self.mlflow_tracker.log_text(str(e), "error.txt")
                raise

    async def stream_message(
        self,
        session_id: str,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        token_callback,
    ) -> ChatGenerationResult:
        """
        메시지 전송 및 스트리밍 응답 생성

        token_callback: async callable(str) -> None, 토큰 단위로 전달
        """
        start_time = time.time()

        # 세션 조회 또는 생성
        session = await self.chat_session_repository.find_by_session_id(session_id)
        if not session:
            session = await self.start_chat_session(metadata={"created_from": "chat"})
            session_id = session.session_id

        # 사용자 메시지 저장
        user_msg = ChatMessage.create_user_message(session_id, user_message)
        await self.chat_message_repository.save(user_msg)

        # 검색 및 법령 정보
        search_result = await self.rag_pipeline.search_use_cases.search_documents(user_message)
        law_result = await self.rag_pipeline.law_information_service.search_related_laws(user_message)
        combined_context = self.rag_pipeline._combine_context(
            search_result.combined_context,
            law_result.context_block
        )

        response_chunks: List[str] = []
        generate_start = time.time()

        if not combined_context.strip():
            fallback = "해당 법률 자료가 아직 준비 중입니다. 곧 추가 후 답변을 제공하겠습니다."
            await token_callback(fallback)
            response_chunks.append(fallback)
        else:
            async for chunk in self.rag_pipeline.llm_service.stream_response(
                query=user_message,
                context=combined_context,
                conversation_history=conversation_history or []
            ):
                token = str(chunk)
                response_chunks.append(token)
                await token_callback(token)

        generate_time = time.time() - generate_start
        total_time = time.time() - start_time
        full_response = "".join(response_chunks)

        assistant_msg = ChatMessage.create_assistant_message(
            session_id=session_id,
            content=full_response,
            retrieve_time=search_result.search_time,
            generate_time=generate_time,
            total_time=total_time,
            context_length=len(combined_context),
            similarity_scores=search_result.similarity_scores,
            retrieved_chunks=search_result.retrieved_chunks
        )

        if law_result.references:
            assistant_msg.metadata["related_laws"] = [asdict(ref) for ref in law_result.references]

        await self.chat_message_repository.save(assistant_msg)

        # 세션 업데이트
        session.increment_message_count()
        await self.chat_session_repository.save(session)

        # 캐시 무효화 (사용자 연동 시)
        if session.user_id and self.chat_cache_service:
            await self.chat_cache_service.invalidate_cache(session.user_id)

        return ChatGenerationResult(
            response=full_response,
            related_laws=law_result.references,
            law_context=law_result.context_block,
            session_id=session_id
        )

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

    async def get_user_chat_history(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> UserChatHistory:
        """
        사용자 채팅 히스토리 조회 (Redis 캐시 활용)

        Args:
            user_id: 사용자 ID
            skip: 건너뛸 개수
            limit: 조회할 최대 개수

        Returns:
            UserChatHistory: 세션 목록과 각 세션별 메시지
        """
        # 1. Redis 캐시 확인
        if self.chat_cache_service:
            cached_data = await self.chat_cache_service.get_chat_history(user_id)
            if cached_data:
                # 캐시 히트
                return self._deserialize_history(cached_data)

        # 2. MySQL에서 조회
        sessions = await self.chat_session_repository.find_by_user_id(user_id, skip, limit)

        # 3. 각 세션의 메시지 조회
        messages_by_session = {}
        for session in sessions:
            messages = await self.chat_message_repository.find_by_session_id(
                session.session_id,
                skip=0,
                limit=100  # 세션당 최대 100개 메시지
            )
            messages_by_session[session.session_id] = messages

        history = UserChatHistory(
            sessions=sessions,
            messages_by_session=messages_by_session
        )

        # 4. Redis에 캐싱
        if self.chat_cache_service:
            serialized = self._serialize_history(history)
            await self.chat_cache_service.set_chat_history(user_id, serialized)

        return history

    def _serialize_history(self, history: UserChatHistory) -> List[Dict[str, Any]]:
        """UserChatHistory를 직렬화"""
        result = []
        for session in history.sessions:
            messages = history.messages_by_session.get(session.session_id, [])
            result.append({
                "session": asdict(session),
                "messages": [asdict(msg) for msg in messages]
            })
        return result

    def _deserialize_history(self, data: List[Dict[str, Any]]) -> UserChatHistory:
        """직렬화된 데이터를 UserChatHistory로 변환"""
        sessions = []
        messages_by_session = {}

        for item in data:
            session_data = item["session"]
            session = ChatSession(**session_data)
            sessions.append(session)

            messages_data = item["messages"]
            messages = [ChatMessage(**msg_data) for msg_data in messages_data]
            messages_by_session[session.session_id] = messages

        return UserChatHistory(
            sessions=sessions,
            messages_by_session=messages_by_session
        )

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
