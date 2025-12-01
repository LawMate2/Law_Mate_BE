from dataclasses import dataclass
from typing import Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from app.chat.application.services.law_information_service import (
    LawInformationService,
    LawSearchResult,
)
from app.chat.application.services.llm_service import LLMService
from app.chat.domain.entities.law_reference import LawReference
from app.search.application.use_cases.search_use_cases import SearchUseCases
from app.search.domain.entities.search_result import SearchResult


class RAGGraphState(TypedDict, total=False):
    """LangGraph 상태 정의"""

    query: str
    history: List[Dict[str, str]]
    has_retrieval: bool
    has_law: bool
    context: str
    law_context: str
    response: str
    combined_context: str
    similarity_scores: List[float]
    retrieved_chunks: int
    search_time: float
    embedding_time: float
    related_laws: List[LawReference]


@dataclass
class RAGPipelineOutput:
    """RAG 그래프 실행 결과"""

    response: str
    combined_context: str
    similarity_scores: List[float]
    retrieved_chunks: int
    retrieval_time: float
    embedding_time: float
    law_context: str
    law_references: List[LawReference]


class LangGraphRAGPipeline:
    """LangGraph 기반 RAG 파이프라인"""

    def __init__(
        self,
        search_use_cases: SearchUseCases,
        llm_service: LLMService,
        law_information_service: LawInformationService,
    ):
        self.search_use_cases = search_use_cases
        self.llm_service = llm_service
        self.law_information_service = law_information_service
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        graph = StateGraph(RAGGraphState)
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("fetch_law_info", self._law_context_node)
        graph.add_node("generate", self._generate_node)

        graph.set_entry_point("retrieve")
        graph.add_edge("retrieve", "fetch_law_info")
        graph.add_edge("fetch_law_info", "generate")
        graph.add_edge("generate", END)
        return graph.compile()

    async def _retrieve_node(self, state: RAGGraphState) -> Dict[str, object]:
        """벡터스토어 검색 노드"""
        search_result: SearchResult = await self.search_use_cases.search_documents(state["query"])
        return {
            "context": search_result.combined_context,
            "has_retrieval": search_result.has_results,
            "similarity_scores": search_result.similarity_scores,
            "retrieved_chunks": search_result.retrieved_chunks,
            "search_time": search_result.search_time,
            "embedding_time": search_result.embedding_time,
        }

    async def _law_context_node(self, state: RAGGraphState) -> Dict[str, object]:
        """법령 컨텍스트 보강 노드"""
        law_result: LawSearchResult = await self.law_information_service.search_related_laws(
            state["query"]
        )
        return {
            "law_context": law_result.context_block,
            "has_law": law_result.has_results,
            "related_laws": law_result.references,
        }

    async def _generate_node(self, state: RAGGraphState) -> Dict[str, object]:
        """LLM 응답 생성 노드"""
        combined_context = self._combine_context(
            state.get("context", ""), state.get("law_context", "")
        )
        has_any_context = bool(combined_context.strip())
        query_text = state.get("query", "") or ""

        # 검색/법령 둘 다 없으면 LLM 호출을 건너뛰고 안전한 응답 제공
        if not has_any_context:
            lower_q = query_text.lower()
            greetings = ["안녕", "안녕하세요", "hello", "hi", "하이"]
            if any(greet in lower_q for greet in greetings) or len(query_text.strip()) <= 6:
                fallback = "안녕하세요! 무엇을 도와드릴까요? 법률 관련 상담이 필요하면 편하게 말씀해주세요."
            else:
                fallback = "해당 법률 자료가 아직 준비 중입니다. 곧 추가 후 답변을 제공하겠습니다."
            return {
                "response": fallback,
                "combined_context": "",
            }

        response = await self.llm_service.generate_response(
            query=state["query"],
            context=combined_context,
            conversation_history=state.get("history", []),
        )
        return {
            "response": response,
            "combined_context": combined_context,
        }

    async def arun(
        self,
        query: str,
        conversation_history: List[Dict[str, str]],
    ) -> RAGPipelineOutput:
        """그래프 실행"""
        final_state = await self.workflow.ainvoke(
            {
                "query": query,
                "history": conversation_history,
            }
        )

        return RAGPipelineOutput(
            response=final_state.get("response", ""),
            combined_context=final_state.get("combined_context", ""),
            similarity_scores=final_state.get("similarity_scores", []) or [],
            retrieved_chunks=final_state.get("retrieved_chunks", 0) or 0,
            retrieval_time=final_state.get("search_time", 0.0) + final_state.get("embedding_time", 0.0),
            embedding_time=final_state.get("embedding_time", 0.0) or 0.0,
            law_context=final_state.get("law_context", "") or "",
            law_references=final_state.get("related_laws", []) or [],
        )

    @staticmethod
    def _combine_context(*segments: str) -> str:
        """컨텍스트를 정돈하여 결합"""
        cleaned = [segment.strip() for segment in segments if segment and segment.strip()]
        return "\n\n".join(cleaned)
