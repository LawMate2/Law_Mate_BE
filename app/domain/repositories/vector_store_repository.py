from abc import ABC, abstractmethod
from typing import List
from ..entities.search_result import SearchResult
from ..value_objects.document_chunk import DocumentChunk
from ..value_objects.embedding_result import EmbeddingResult


class VectorStoreRepository(ABC):
    """벡터 저장소 인터페이스"""

    @abstractmethod
    async def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """문서 청크들을 벡터 저장소에 추가"""
        pass

    @abstractmethod
    async def search_similar(self, query: str, k: int = 3) -> SearchResult:
        """유사한 문서 검색"""
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """텍스트 임베딩 생성"""
        pass

    @abstractmethod
    async def delete_documents(self, document_id: str) -> bool:
        """문서 삭제"""
        pass

    @abstractmethod
    async def get_document_count(self) -> int:
        """저장된 문서 청크 수"""
        pass

    @abstractmethod
    async def list_documents(self) -> List[str]:
        """저장된 문서 목록"""
        pass

    @abstractmethod
    async def clear_all(self) -> bool:
        """모든 문서 삭제"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """헬스 체크"""
        pass