from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.chat.application.use_cases.chat_use_cases import ChatUseCases
from app.chat.presentation.schemas.chat_schemas import (
    ChatMessageSchema,
    ChatRequest,
    ChatResponse,
    ChatSessionSchema,
    ChatHistoryResponse,
    LawReferenceSchema,
)
from pydantic import BaseModel
from typing import List, Literal, Optional
from app.db.database import get_db
from app.shared.dependencies import get_chat_use_cases


class MCPAnalysisRequest(BaseModel):
    """MCP 작업을 위한 AI 분석 요청"""
    task_type: Literal["gmail", "calendar", "drive"]
    conversation_messages: List[ChatMessageSchema]


class MCPAnalysisResponse(BaseModel):
    """MCP 작업을 위한 AI 분석 응답"""
    task_type: str
    extracted_data: dict
    confidence: str  # "high", "medium", "low"
    suggestions: Optional[str] = None


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
                chat_result = await chat_use_cases.send_message(
                    session_id=session_id,
                    user_message=request.message,
                    conversation_history=conversation_history
                )

                # 새로운 대화 기록 생성
                updated_history = conversation_history + [
                    {"role": "user", "content": request.message},
                    {"role": "assistant", "content": chat_result.response}
                ]

                return ChatResponse(
                    response=chat_result.response,
                    session_id=session_id,
                    conversation_history=[
                        ChatMessageSchema(role=msg["role"], content=msg["content"])
                        for msg in updated_history
                    ],
                    related_laws=[
                        LawReferenceSchema(**asdict(law))
                        for law in chat_result.related_laws
                    ],
                    law_context=chat_result.law_context
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

        @self.router.get("/history/user/{user_id}", response_model=ChatHistoryResponse)
        async def get_user_chat_history(
            user_id: int,
            skip: int = 0,
            limit: int = 100,
            chat_use_cases: ChatUseCases = Depends(get_chat_use_cases)
        ):
            """사용자 채팅 히스토리 조회 (Redis 캐시 + MySQL)"""
            try:
                history = await chat_use_cases.get_user_chat_history(user_id, skip, limit)

                # 프론트 형식에 맞게 변환
                chats = []
                for session in history.sessions:
                    messages = history.messages_by_session.get(session.session_id, [])
                    chats.append(
                        ChatSessionSchema(
                            id=session.session_id,
                            title=session.title or "새로운 상담",
                            messages=[
                                ChatMessageSchema(
                                    id=str(msg.id) if msg.id else str(idx),
                                    role=msg.role.value,
                                    content=msg.content
                                )
                                for idx, msg in enumerate(messages)
                            ],
                            created_at=session.created_at,
                            updated_at=session.updated_at
                        )
                    )

                return ChatHistoryResponse(
                    chats=chats,
                    total=len(chats)
                )

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"사용자 히스토리 조회 중 오류: {str(e)}")

        @self.router.get("/statistics")
        async def get_chat_statistics(
            chat_use_cases: ChatUseCases = Depends(get_chat_use_cases)
        ):
            """채팅 통계"""
            try:
                return await chat_use_cases.get_chat_statistics()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"통계 조회 중 오류: {str(e)}")

        @self.router.websocket("/ws")
        async def chat_stream(
            websocket: WebSocket,
            chat_use_cases: ChatUseCases = Depends(get_chat_use_cases)
        ):
            """웹소켓 기반 스트리밍 채팅"""
            await websocket.accept()
            try:
                while True:
                    payload = await websocket.receive_json()
                    message = payload.get("message")
                    session_id = payload.get("session_id")
                    conversation_history = payload.get("conversation_history") or []

                    if not message:
                        await websocket.send_json({"event": "error", "detail": "message가 필요합니다."})
                        continue

                    async def send_token(token: str):
                        await websocket.send_json({"event": "token", "token": token})

                    try:
                        result = await chat_use_cases.stream_message(
                            session_id=session_id or "",
                            user_message=message,
                            conversation_history=conversation_history,
                            token_callback=send_token
                        )
                        await websocket.send_json({
                            "event": "done",
                            "session_id": result.session_id or session_id or "",
                            "response": result.response,
                            "related_laws": [asdict(law) for law in result.related_laws],
                            "law_context": result.law_context
                        })
                    except Exception as exc:
                        await websocket.send_json({"event": "error", "detail": str(exc)})
            except WebSocketDisconnect:
                return

        @self.router.post("/analyze-for-mcp", response_model=MCPAnalysisResponse)
        async def analyze_conversation_for_mcp(
            request: MCPAnalysisRequest,
            chat_use_cases: ChatUseCases = Depends(get_chat_use_cases)
        ):
            """대화 내용을 AI로 분석하여 MCP 작업에 필요한 정보 추출"""
            try:
                # 대화 내용을 텍스트로 변환
                conversation_text = "\n".join([
                    f"{msg.role}: {msg.content}"
                    for msg in request.conversation_messages[-5:]  # 최근 5개 메시지만 사용
                ])

                # 작업 타입별 프롬프트 생성
                prompts = {
                    "gmail": f"""다음 대화 내용을 분석하여 이메일 작성에 필요한 정보를 JSON 형식으로 추출해주세요.

대화 내용:
{conversation_text}

다음 정보를 추출해주세요:
1. recipient (받는 사람 이메일 주소)
2. subject (이메일 제목)
3. body (이메일 본문 - 전문적이고 예의바른 형식으로)

JSON 형식으로만 응답해주세요. 예시:
{{"recipient": "example@email.com", "subject": "계약서 검토 요청", "body": "안녕하세요,\\n\\n계약서 검토를 요청드립니다...\\n\\n감사합니다."}}""",

                    "calendar": f"""다음 대화 내용을 분석하여 일정 등록에 필요한 정보를 JSON 형식으로 추출해주세요.

대화 내용:
{conversation_text}

다음 정보를 추출해주세요:
1. eventTitle (일정 제목)
2. eventDate (시작 일시, ISO 8601 형식: YYYY-MM-DDTHH:mm)
3. eventEnd (종료 일시, ISO 8601 형식, 없으면 시작시간 +1시간)
4. eventDescription (일정 설명)

JSON 형식으로만 응답해주세요. 날짜가 명확하지 않으면 오늘 날짜를 기준으로 해주세요. 예시:
{{"eventTitle": "계약서 검토 미팅", "eventDate": "2024-12-03T14:00", "eventEnd": "2024-12-03T15:00", "eventDescription": "계약서 검토 및 논의"}}""",

                    "drive": f"""다음 대화 내용을 분석하여 파일 업로드에 필요한 정보를 JSON 형식으로 추출해주세요.

대화 내용:
{conversation_text}

다음 정보를 추출해주세요:
1. contractName (파일/계약서 이름)
2. folderName (저장할 폴더명, 기본값: "Contracts")

JSON 형식으로만 응답해주세요. 예시:
{{"contractName": "2024년 서비스 계약서", "folderName": "Contracts"}}"""
                }

                # AI를 사용하여 정보 추출
                analysis_query = prompts[request.task_type]
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.conversation_messages[:-5]  # 이전 대화는 컨텍스트로
                ]

                result = await chat_use_cases.send_message(
                    session_id=None,
                    user_message=analysis_query,
                    conversation_history=conversation_history
                )

                # JSON 추출 시도
                response_text = result.response
                extracted_data = {}
                confidence = "low"
                suggestions = None

                try:
                    # JSON 블록 찾기
                    import json
                    import re

                    # ```json ... ``` 또는 { ... } 패턴 찾기
                    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # 직접 JSON 찾기
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                        else:
                            json_str = response_text

                    extracted_data = json.loads(json_str)

                    # 신뢰도 평가
                    required_fields = {
                        "gmail": ["recipient", "subject", "body"],
                        "calendar": ["eventTitle", "eventDate"],
                        "drive": ["contractName"]
                    }

                    required = required_fields[request.task_type]
                    if all(field in extracted_data and extracted_data[field] for field in required):
                        confidence = "high"
                    elif any(field in extracted_data and extracted_data[field] for field in required):
                        confidence = "medium"
                        suggestions = f"일부 필수 정보가 누락되었습니다. {', '.join(required)} 정보를 확인해주세요."
                    else:
                        confidence = "low"
                        suggestions = "대화에서 충분한 정보를 찾을 수 없습니다. 추가 정보를 입력해주세요."

                except (json.JSONDecodeError, AttributeError) as e:
                    # JSON 파싱 실패 시 기본값 반환
                    extracted_data = {}
                    confidence = "low"
                    suggestions = "AI가 정보를 추출하지 못했습니다. 수동으로 입력해주세요."

                return MCPAnalysisResponse(
                    task_type=request.task_type,
                    extracted_data=extracted_data,
                    confidence=confidence,
                    suggestions=suggestions
                )

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"MCP 분석 중 오류: {str(e)}")
