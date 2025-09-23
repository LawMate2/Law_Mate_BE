from abc import ABC, abstractmethod
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


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
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 도움이 되는 AI 어시스턴트입니다.
            주어진 컨텍스트를 바탕으로 사용자의 질문에 답변해주세요.

            컨텍스트: {context}"""),
            ("human", "{query}")
        ])

        chain = prompt | self.llm
        response = chain.invoke({
            "context": context,
            "query": query
        })

        return response.content