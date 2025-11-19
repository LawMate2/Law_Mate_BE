from abc import ABC, abstractmethod
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader

from app.documents.domain.value_objects.document_chunk import DocumentChunk


class DocumentProcessor(ABC):
    """문서 처리 서비스 인터페이스"""

    @abstractmethod
    async def process_document(self, file_path: str) -> List[DocumentChunk]:
        """문서를 처리하여 청크들로 분할"""
        pass


class LangChainDocumentProcessor(DocumentProcessor):
    """LangChain을 사용한 문서 처리기"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    async def process_document(self, file_path: str) -> List[DocumentChunk]:
        """문서를 처리하여 청크들로 분할"""
        # 파일 확장자에 따른 로더 선택
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        elif file_path.endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {file_path}")

        # 문서 로드
        documents = loader.load()

        # 텍스트 분할
        texts = self.text_splitter.split_documents(documents)

        # DocumentChunk 객체들로 변환
        chunks = []
        for i, text in enumerate(texts):
            chunk_id = f"{file_path}_{i}"
            chunk = DocumentChunk(
                content=text.page_content,
                chunk_id=chunk_id,
                source=file_path,
                page=getattr(text, 'metadata', {}).get('page', 0),
                metadata=getattr(text, 'metadata', {})
            )
            chunks.append(chunk)

        return chunks
