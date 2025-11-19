import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict

import httpx
from langgraph.graph import END, StateGraph

from app.chat.domain.entities.law_reference import LawReference

logger = logging.getLogger(__name__)


@dataclass
class LawSearchResult:
    """법령 조회 결과"""

    references: List[LawReference]
    context_block: str = ""

    @property
    def has_results(self) -> bool:
        return len(self.references) > 0

    @classmethod
    def empty(cls) -> "LawSearchResult":
        return cls(references=[], context_block="")


class LawInformationService(ABC):
    """법령 정보 서비스 인터페이스"""

    @abstractmethod
    async def search_related_laws(
        self,
        query: str,
        max_results: int = 3
    ) -> LawSearchResult:
        """질문과 연관된 법령 조회"""
        raise NotImplementedError


class LawGraphState(TypedDict, total=False):
    """LangGraph 상태"""

    query: str
    max_results: int
    raw_payload: Any
    references: List[LawReference]
    context_block: str


class AssemblyLawInformationService(LawInformationService):
    """의회·법률정보 포털 Open API 연동 서비스"""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        query_param: str = "search",
        default_params: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.query_param = query_param
        self.default_params = default_params or {"type": "json"}
        self.timeout = timeout
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        workflow = StateGraph(LawGraphState)
        workflow.add_node("retrieve", self._retrieve_laws_node)
        workflow.add_node("format", self._format_context_node)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "format")
        workflow.add_edge("format", END)
        return workflow.compile()

    async def search_related_laws(
        self,
        query: str,
        max_results: int = 3
    ) -> LawSearchResult:
        if not self.api_key or not self.base_url:
            logger.debug("법령 API 설정이 비어 있어 조회를 건너뜁니다.")
            return LawSearchResult.empty()

        state = await self.workflow.ainvoke({
            "query": query,
            "max_results": max_results
        })
        references = state.get("references", []) or []
        context_block = state.get("context_block", "") or ""
        return LawSearchResult(references=references, context_block=context_block)

    async def _retrieve_laws_node(self, state: LawGraphState) -> Dict[str, Any]:
        """API 호출 노드"""
        max_results = state.get("max_results", 3)
        try:
            payload = await self._request_portal(state["query"], max_results)
            references = self._parse_references(payload, max_results)
            return {
                "raw_payload": payload,
                "references": references
            }
        except Exception as exc:
            logger.warning("법령 API 호출 중 오류가 발생했습니다: %s", exc, exc_info=True)
            return {"references": []}

    async def _format_context_node(self, state: LawGraphState) -> Dict[str, Any]:
        """컨텍스트 포맷 노드"""
        references = state.get("references") or []
        if not references:
            return {"context_block": ""}

        lines: List[str] = ["[관련 법령 요약]"]
        for idx, reference in enumerate(references, start=1):
            lines.append(f"({idx}) {reference.to_context_block()}")
        return {"context_block": "\n\n".join(lines)}

    async def _request_portal(self, query: str, max_results: int) -> Any:
        """의회·법률정보 포털 API 호출"""
        params = dict(self.default_params)
        params[self.query_param] = query

        # 서비스별 페이징 파라미터를 자동 설정
        if "numOfRows" in params:
            params["numOfRows"] = max_results
        elif "perPage" in params:
            params["perPage"] = max_results
        else:
            params["numOfRows"] = max_results

        params.setdefault("pageNo", 1)
        params.setdefault("type", "json")
        params["serviceKey"] = self.api_key

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            if "json" in (params.get("type") or "").lower():
                return response.json()
            return response.text

    def _parse_references(self, payload: Any, max_results: int) -> List[LawReference]:
        """API 응답에서 핵심 필드 추출"""
        rows = self._extract_rows(payload)
        references: List[LawReference] = []
        for row in rows[:max_results]:
            reference = self._row_to_reference(row)
            if reference:
                references.append(reference)
        return references

    def _extract_rows(self, payload: Any) -> List[Dict[str, Any]]:
        """응답 내 리스트 탐색"""
        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            if "row" in payload and isinstance(payload["row"], list):
                return payload["row"]
            for value in payload.values():
                rows = self._extract_rows(value)
                if rows:
                    return rows

        return []

    def _row_to_reference(self, row: Dict[str, Any]) -> Optional[LawReference]:
        """단일 행을 LawReference로 변환"""
        if not isinstance(row, dict):
            return None

        def pick(*keys: str) -> Optional[str]:
            for key in keys:
                if key in row and row[key]:
                    return str(row[key]).strip()
            return None

        law_name = pick(
            "lawName", "lawNm", "LAW_NAME", "법령명",
            "LAWSUBJECT", "title"
        )
        if not law_name:
            return None

        article = pick("article", "조문", "조항", "조문명", "articleName")
        summary = pick("summary", "요약", "content", "내용", "법령내용")
        reference_url = pick("reference", "url", "link", "LAW_URL")
        provider = pick("provider", "제공기관", "기관명")

        return LawReference(
            law_name=law_name,
            article=article,
            summary=summary,
            reference_url=reference_url,
            provider=provider
        )
