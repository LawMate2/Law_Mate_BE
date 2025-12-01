import json
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI


class TextAnalysisService:
    """OCR 텍스트를 AI로 분석하는 서비스 (RAG 지원)"""

    def __init__(self, api_key: str, search_use_cases=None):
        self.client = AsyncOpenAI(api_key=api_key)
        self.search_use_cases = search_use_cases

    async def _search_knowledge_base(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """
        지식베이스에서 관련 법률 정보 검색

        Args:
            text: 검색할 텍스트

        Returns:
            검색 결과 리스트 (없으면 None)
        """
        if not self.search_use_cases:
            return None

        try:
            # 텍스트의 주요 키워드를 추출해서 검색
            # 전체 텍스트가 너무 길 수 있으므로 요약해서 검색
            search_query = text[:500]  # 처음 500자만 사용

            results = await self.search_use_cases.search(
                query=search_query,
                top_k=3  # 상위 3개 결과만 사용
            )

            if results and len(results) > 0:
                return [
                    {
                        "content": result.get("content", ""),
                        "metadata": result.get("metadata", {})
                    }
                    for result in results
                ]
            return None

        except Exception as e:
            print(f"지식베이스 검색 중 오류 (무시하고 계속): {e}")
            return None

    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        OCR로 추출된 텍스트를 분석하여 주의사항과 권장사항을 제공
        지식베이스가 있으면 관련 법률 정보를 참고하여 분석

        Args:
            text: OCR로 추출된 텍스트

        Returns:
            Dict: 분석 결과 (요약, 문서 유형, 주의사항, 권장사항)
        """

        # 1. 지식베이스에서 관련 정보 검색
        knowledge_base_results = await self._search_knowledge_base(text)

        # 2. 시스템 프롬프트 구성
        system_prompt = """당신은 법률 문서 분석 전문가입니다.
OCR로 추출된 텍스트를 분석하여 다음을 제공하세요:
1. 문서 요약
2. 문서 유형 판단
3. 주의해야 할 핵심 포인트 (제목, 설명, 중요도)
4. 권장사항

반드시 JSON 형식으로만 응답하세요."""

        # 3. 유저 프롬프트 구성 (지식베이스 정보 포함)
        user_prompt_parts = []

        if knowledge_base_results:
            user_prompt_parts.append("### 참고할 법률 정보:")
            for idx, kb_result in enumerate(knowledge_base_results, 1):
                user_prompt_parts.append(f"\n[참고자료 {idx}]")
                user_prompt_parts.append(kb_result["content"][:1000])  # 각 결과당 최대 1000자
            user_prompt_parts.append("\n---\n")

        user_prompt_parts.append(f"""### 분석할 문서 텍스트:

{text}

---

위 문서를 분석하여 다음 JSON 형식으로 응답하세요:
{{
    "summary": "문서 요약 (2-3문장)",
    "document_type": "문서 유형 (예: 계약서, 고지서, 영수증, 안내문 등)",
    "key_points": [
        {{
            "title": "주의사항 제목",
            "description": "상세 설명 (참고자료가 있다면 관련 법률 조항도 언급)",
            "importance": "high|medium|low"
        }}
    ],
    "recommendations": [
        "권장사항 1 (참고자료 기반)",
        "권장사항 2"
    ]
}}""")

        user_prompt = "\n".join(user_prompt_parts)

        # 4. AI 분석 수행
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            return result

        except Exception as e:
            raise Exception(f"텍스트 분석 중 오류 발생: {str(e)}")
