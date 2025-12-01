from abc import ABC, abstractmethod
import json
from typing import List, Dict, AsyncIterator, Any, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from openai import AsyncOpenAI

from app.shared.services.mcp_client import MCPClient


class LLMService(ABC):
    """LLM 서비스 인터페이스"""

    @abstractmethod
    async def generate_response(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """응답 생성"""
        pass


class OpenAILLMService(LLMService):
    """OpenAI를 사용한 LLM 서비스"""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", temperature: float = 0.7):
        self.llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=temperature
        )

    async def generate_response(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """응답 생성"""
        # 대화 내역을 LLM 메시지 형식으로 변환
        history_messages = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role")
                content = msg.get("content", "")
                if not content:
                    continue
                if role == "assistant":
                    history_messages.append(AIMessage(content=content))
                else:
                    history_messages.append(HumanMessage(content=content))

        # 법률 전문가 톤을 강제하는 시스템 프롬프트
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """당신은 한국 법률 전문가 AI 어시스턴트입니다. 한글 존댓말로 친근하게 답변합니다.

**법률 질문일 때:**
- 제공된 컨텍스트(법령/판례/지식베이스)를 근거로 전문적이고 신뢰도 높게 답변
- 근거가 있을 때: 핵심 요지 → 관련 법령/조문 번호 → 필요한 경우 추가 설명 순으로 간결히 제시
- 근거가 부족할 때: "제공된 정보로는 확정하기 어렵습니다."라고 명시하고 추가로 필요한 정보나 절차를 안내
- 추측 금지, 단정이 어려우면 조건부로 설명

**일반 대화일 때:**
- 인사, 안부, 잡담 등은 자연스럽고 친근하게 응답
- 법률과 무관한 일상적인 질문도 상식 범위 내에서 답변
- 법률 근거 요구 없이 편하게 대화

참고 컨텍스트:
{context}
"""
            ),
            MessagesPlaceholder(variable_name="history"),
            (
                "human",
                "{query}"
            ),
        ])

        chain = prompt | self.llm
        response = chain.invoke({
            "context": context,
            "query": query,
            "history": history_messages
        })

        return response.content

    async def stream_response(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> AsyncIterator[str]:
        """응답을 토큰 단위로 스트리밍"""
        history_messages = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role")
                content = msg.get("content", "")
                if not content:
                    continue
                if role == "assistant":
                    history_messages.append(AIMessage(content=content))
                else:
                    history_messages.append(HumanMessage(content=content))

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """당신은 한국 법률 전문가 AI 어시스턴트입니다. 한글 존댓말로 친근하게 답변합니다.

**법률 질문일 때:**
- 제공된 컨텍스트(법령/판례/지식베이스)를 근거로 전문적이고 신뢰도 높게 답변
- 근거가 있을 때: 핵심 요지 → 관련 법령/조문 번호 → 필요한 경우 추가 설명 순으로 간결히 제시
- 근거가 부족할 때: "제공된 정보로는 확정하기 어렵습니다."라고 명시하고 추가로 필요한 정보나 절차를 안내
- 추측 금지, 단정이 어려우면 조건부로 설명

**일반 대화일 때:**
- 인사, 안부, 잡담 등은 자연스럽고 친근하게 응답
- 법률과 무관한 일상적인 질문도 상식 범위 내에서 답변
- 법률 근거 요구 없이 편하게 대화

참고 컨텍스트:
{context}
"""
            ),
            MessagesPlaceholder(variable_name="history"),
            (
                "human",
                "{query}"
            ),
        ])

        chain = prompt | self.llm
        async for chunk in chain.astream({
            "context": context,
            "query": query,
            "history": history_messages
        }):
            # chunk는 BaseMessageChunk 형태로 content에 누적 텍스트가 담김
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content


class ToolCallingLLMService(LLMService):
    """
    MCP 도구 호출을 지원하는 OpenAI LLM 서비스.
    - Gmail/Calendar/Drive 등 외부 작업은 도구 호출로 처리
    - 일반 질의는 컨텍스트 기반 답변
    """

    def __init__(
        self,
        api_key: str,
        mcp_client: MCPClient,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.mcp_client = mcp_client

    async def _list_tools(self) -> List[Dict[str, Any]]:
        """MCP 도구를 OpenAI function 사양으로 변환"""
        tools = await self.mcp_client.list_tools()
        converted = []
        for tool in tools:
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema or {"type": "object"},
                    },
                }
            )
        return converted

    @staticmethod
    def _build_history(conversation_history: Optional[List[Dict[str, str]]]):
        history = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role")
                content = msg.get("content", "")
                if not content:
                    continue
                if role == "assistant":
                    history.append({"role": "assistant", "content": content})
                else:
                    history.append({"role": "user", "content": content})
        return history

    @staticmethod
    def _render_tool_output(result: Any) -> str:
        """MCP 도구 결과를 문자열로 정돈"""
        try:
            if isinstance(result, list):
                # MCP TextContent 목록 형태일 수 있음
                fragments = []
                for item in result:
                    text = getattr(item, "text", None) or getattr(item, "content", None)
                    fragments.append(text or str(item))
                return "\n".join(fragments)
            if isinstance(result, dict):
                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except Exception:
            return str(result)

    def _system_messages(self, context: str) -> List[Dict[str, str]]:
        """시스템 메시지 구성"""
        context_block = context or "제공된 컨텍스트 없음"
        return [
            {
                "role": "system",
                "content": (
                    "당신은 한국 법률 전문가 AI 어시스턴트입니다. 한글 존댓말로 친근하게 답변합니다.\n\n"
                    "**법률 질문일 때:** 제공된 컨텍스트를 근거로 전문적이고 신뢰도 높게 답변합니다.\n"
                    "**일반 대화일 때:** 인사, 안부, 잡담 등은 자연스럽고 친근하게 응답합니다. "
                    "법률과 무관한 일상적인 질문도 상식 범위 내에서 답변합니다.\n\n"
                    "메일 발송/일정 등록/드라이브 업로드 등 실행 요청이 있을 때만 도구를 호출하세요. "
                    "도구 결과는 사용자에게 짧게 요약해 전달하세요."
                ),
            },
            {
                "role": "system",
                "content": f"참고 컨텍스트:\n{context_block}",
            },
        ]

    async def _run_chat_with_tools(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> str:
        try:
            tools = await self._list_tools()
        except Exception:
            # MCP 연결 실패 시 도구 없이 응답
            tools = []
        messages: List[Dict[str, Any]] = self._system_messages(context)
        messages.extend(self._build_history(conversation_history))
        messages.append(
            {
                "role": "user",
                "content": query,
            }
        )

        # tool 호출 루프
        while True:
            # tools가 있을 때만 tool_choice 파라미터 전달
            completion_params = {
                "model": self.model,
                "temperature": self.temperature,
                "messages": messages,
            }
            if tools:
                completion_params["tools"] = tools
                completion_params["tool_choice"] = "auto"

            completion = await self.client.chat.completions.create(**completion_params)
            choice = completion.choices[0]
            message = choice.message
            finish = choice.finish_reason

            if finish == "tool_calls" and message.tool_calls:
                # 어시스턴트의 tool_calls 메시지를 추가
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in message.tool_calls
                        ],
                    }
                )

                # 각 도구 실행 후 결과 추가
                for tool_call in message.tool_calls:
                    arguments = {}
                    if tool_call.function.arguments:
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                    try:
                        tool_result = await self.mcp_client.call_tool(
                            tool_call.function.name, arguments
                        )
                        tool_output = self._render_tool_output(tool_result)
                    except Exception as exc:
                        tool_output = f"tool_call_error: {exc}"

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_output,
                        }
                    )
                # 도구 결과를 포함한 다음 라운드
                continue

            # 일반 응답 반환
            return message.content or ""

    async def generate_response(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> str:
        return await self._run_chat_with_tools(query, context, conversation_history)

    async def stream_response(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> AsyncIterator[str]:
        # 스트리밍 인터페이스를 유지하기 위해 최종 응답 한 번만 전달
        final_response = await self._run_chat_with_tools(query, context, conversation_history)
        yield final_response
