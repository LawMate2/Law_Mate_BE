from abc import ABC, abstractmethod
from typing import List, Dict, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


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
                """당신은 한국 법률 전문가 AI입니다. 전문적이고 신뢰도 높은 어투로 답변합니다.
컨텍스트(법령/판례/지식베이스)를 반드시 근거로 활용하고, 추측은 금지합니다.
- 근거가 있을 때: 핵심 요지 → 관련 법령/조문 번호 → 필요한 경우 추가 설명 순으로 간결히 제시
- 근거가 부족할 때: "제공된 정보로는 확정하기 어렵습니다."라고 명시하고 추가로 필요한 정보나 절차를 안내
- 과장 금지, 단정이 어려우면 조건부로 설명
- 한글 존댓말로 응답

참고 컨텍스트:
{context}
"""
            ),
            MessagesPlaceholder(variable_name="history"),
            (
                "human",
                """사용자 질문: {query}

위 컨텍스트를 근거로 답변하되, 컨텍스트에 없으면 추측하지 말고 부족함을 밝혀주세요."""
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
                """당신은 한국 법률 전문가 AI입니다. 전문적이고 신뢰도 높은 어투로 답변합니다.
컨텍스트(법령/판례/지식베이스)를 반드시 근거로 활용하고, 추측은 금지합니다.
- 근거가 있을 때: 핵심 요지 → 관련 법령/조문 번호 → 필요한 경우 추가 설명 순으로 간결히 제시
- 근거가 부족할 때: "제공된 정보로는 확정하기 어렵습니다."라고 명시하고 추가로 필요한 정보나 절차를 안내
- 과장 금지, 단정이 어려우면 조건부로 설명
- 한글 존댓말로 응답

참고 컨텍스트:
{context}
"""
            ),
            MessagesPlaceholder(variable_name="history"),
            (
                "human",
                """사용자 질문: {query}

위 컨텍스트를 근거로 답변하되, 컨텍스트에 없으면 추측하지 말고 부족함을 밝혀주세요."""
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
