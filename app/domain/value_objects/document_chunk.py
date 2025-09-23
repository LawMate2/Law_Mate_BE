from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class DocumentChunk:
    """문서 청크 값 객체"""
    content: str
    chunk_id: str
    source: str
    page: int
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})

    @property
    def content_length(self) -> int:
        return len(self.content)

    @property
    def is_empty(self) -> bool:
        return len(self.content.strip()) == 0

    def get_preview(self, length: int = 100) -> str:
        """청크 내용 미리보기"""
        if len(self.content) <= length:
            return self.content
        return self.content[:length] + "..."