from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.document import Document


class DocumentRepository(ABC):
    """문서 저장소 인터페이스"""

    @abstractmethod
    async def save(self, document: Document) -> Document:
        """문서 저장"""
        pass

    @abstractmethod
    async def find_by_id(self, document_id: int) -> Optional[Document]:
        """ID로 문서 조회"""
        pass

    @abstractmethod
    async def find_by_filename(self, filename: str) -> Optional[Document]:
        """파일명으로 문서 조회"""
        pass

    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> List[Document]:
        """모든 문서 조회"""
        pass

    @abstractmethod
    async def delete(self, document_id: int) -> bool:
        """문서 삭제"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """문서 총 개수"""
        pass

    @abstractmethod
    async def find_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Document]:
        """상태별 문서 조회"""
        pass