from dataclasses import dataclass
from typing import Optional


@dataclass
class LawReference:
    """의회·법률정보 포털에서 조회한 법령 요약"""

    law_name: str
    article: Optional[str] = None
    summary: Optional[str] = None
    reference_url: Optional[str] = None
    provider: Optional[str] = None

    def to_context_block(self) -> str:
        """LLM 컨텍스트에 삽입 가능한 문자열"""
        parts = [f"법령명: {self.law_name}"]
        if self.article:
            parts.append(f"조문/조항: {self.article}")
        if self.summary:
            parts.append(f"요약: {self.summary}")
        if self.reference_url:
            parts.append(f"원문: {self.reference_url}")
        if self.provider:
            parts.append(f"제공기관: {self.provider}")
        return "\n".join(parts)
