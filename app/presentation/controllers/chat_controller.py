from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session

from ...application.use_cases.chat_use_cases import ChatUseCases
from ...db.database import get_db
from ..schemas.chat_schemas import ChatRequest, ChatResponse, ChatMessageSchema
from ..dependencies import get_chat_use_cases


class ChatController:
    """채팅 컨트롤러"""

    def __init__(self):
        self.router = APIRouter(prefix="/chat", tags=["chat"])
        self._register_routes()

    def _register_routes(self):
        """라우트 등록"""

        @self.router.post("/", response_model=ChatResponse)
        async def send_message(
            request: ChatRequest,
            chat_use_cases: ChatUseCases = Depends(get_chat_use_cases),
            db: Session = Depends(get_db)
        ):
            """메시지 전송"""
            try:
                # 대화 기록을 딕셔너리 형태로 변환
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.conversation_history
                ]

                # 세션이 없으면 새로 생성
                session_id = request.session_id
                if not session_id:
                    session = await chat_use_cases.start_chat_session()
                    session_id = session.session_id

                # 응답 생성
                response = await chat_use_cases.send_message(
                    session_id=session_id,
                    user_message=request.message,
                    conversation_history=conversation_history
                )

                # 새로운 대화 기록 생성
                updated_history = conversation_history + [
                    {"role": "user", "content": request.message},
                    {"role": "assistant", "content": response}
                ]

                return ChatResponse(
                    response=response,
                    session_id=session_id,
                    conversation_history=[
                        ChatMessageSchema(role=msg["role"], content=msg["content"])
                        for msg in updated_history
                    ]
                )

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"채팅 처리 중 오류: {str(e)}")

        @self.router.get("/sessions/{session_id}/history")
        async def get_chat_history(
            session_id: str,
            skip: int = 0,
            limit: int = 100,
            chat_use_cases: ChatUseCases = Depends(get_chat_use_cases)
        ):
            """채팅 히스토리 조회"""
            try:
                messages = await chat_use_cases.get_chat_history(session_id, skip, limit)
                return [
                    ChatMessageSchema(role=msg.role.value, content=msg.content)
                    for msg in messages
                ]
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"히스토리 조회 중 오류: {str(e)}")

        @self.router.get("/sessions")
        async def list_sessions(
            skip: int = 0,
            limit: int = 100,
            chat_use_cases: ChatUseCases = Depends(get_chat_use_cases)
        ):
            """세션 목록 조회"""
            try:
                sessions = await chat_use_cases.list_sessions(skip, limit)
                return [
                    {
                        "session_id": session.session_id,
                        "created_at": session.created_at,
                        "total_messages": session.total_messages
                    }
                    for session in sessions
                ]
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"세션 목록 조회 중 오류: {str(e)}")

        @self.router.delete("/sessions/{session_id}")
        async def delete_session(
            session_id: str,
            chat_use_cases: ChatUseCases = Depends(get_chat_use_cases)
        ):
            """세션 삭제"""
            try:
                success = await chat_use_cases.delete_session(session_id)
                if success:
                    return {"message": "세션이 성공적으로 삭제되었습니다."}
                else:
                    raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"세션 삭제 중 오류: {str(e)}")

        @self.router.get("/statistics")
        async def get_chat_statistics(
            chat_use_cases: ChatUseCases = Depends(get_chat_use_cases)
        ):
            """채팅 통계"""
            try:
                return await chat_use_cases.get_chat_statistics()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"통계 조회 중 오류: {str(e)}")