from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ...domain.entities.document import Document, DocumentStatus
from ...domain.repositories.document_repository import DocumentRepository
from ...db.models import Document as DocumentModel


class SqlAlchemyDocumentRepository(DocumentRepository):
    """SQLAlchemy를 사용한 문서 저장소 구현"""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def save(self, document: Document) -> Document:
        """문서 저장"""
        if document.id is None:
            # 새 문서 생성
            db_document = DocumentModel(
                filename=document.filename,
                file_path=document.file_path,
                file_size=document.file_size,
                file_type=document.file_type,
                upload_time=document.upload_time,
                chunk_count=document.chunk_count,
                processing_time=document.processing_time,
                is_processed=document.is_processed,
                metadata=document.metadata
            )
            self.db.add(db_document)
            self.db.commit()
            self.db.refresh(db_document)
            document.id = db_document.id
        else:
            # 기존 문서 업데이트
            db_document = self.db.query(DocumentModel).filter(
                DocumentModel.id == document.id
            ).first()
            if db_document:
                db_document.filename = document.filename
                db_document.file_path = document.file_path
                db_document.file_size = document.file_size
                db_document.file_type = document.file_type
                db_document.upload_time = document.upload_time
                db_document.chunk_count = document.chunk_count
                db_document.processing_time = document.processing_time
                db_document.is_processed = document.is_processed
                db_document.metadata = document.metadata
                self.db.commit()

        return document

    async def find_by_id(self, document_id: int) -> Optional[Document]:
        """ID로 문서 조회"""
        db_document = self.db.query(DocumentModel).filter(
            DocumentModel.id == document_id
        ).first()

        if db_document:
            return self._to_domain_entity(db_document)
        return None

    async def find_by_filename(self, filename: str) -> Optional[Document]:
        """파일명으로 문서 조회"""
        db_document = self.db.query(DocumentModel).filter(
            DocumentModel.filename == filename
        ).first()

        if db_document:
            return self._to_domain_entity(db_document)
        return None

    async def find_all(self, skip: int = 0, limit: int = 100) -> List[Document]:
        """모든 문서 조회"""
        db_documents = self.db.query(DocumentModel).offset(skip).limit(limit).all()
        return [self._to_domain_entity(doc) for doc in db_documents]

    async def delete(self, document_id: int) -> bool:
        """문서 삭제"""
        db_document = self.db.query(DocumentModel).filter(
            DocumentModel.id == document_id
        ).first()

        if db_document:
            self.db.delete(db_document)
            self.db.commit()
            return True
        return False

    async def count(self) -> int:
        """문서 총 개수"""
        return self.db.query(DocumentModel).count()

    async def find_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Document]:
        """상태별 문서 조회"""
        is_processed = status == DocumentStatus.COMPLETED.value
        db_documents = self.db.query(DocumentModel).filter(
            DocumentModel.is_processed == is_processed
        ).offset(skip).limit(limit).all()
        return [self._to_domain_entity(doc) for doc in db_documents]

    def _to_domain_entity(self, db_document: DocumentModel) -> Document:
        """DB 모델을 도메인 엔티티로 변환"""
        status = DocumentStatus.COMPLETED if db_document.is_processed else DocumentStatus.PENDING

        return Document(
            id=db_document.id,
            filename=db_document.filename,
            file_path=db_document.file_path,
            file_size=db_document.file_size,
            file_type=db_document.file_type,
            upload_time=db_document.upload_time,
            chunk_count=db_document.chunk_count,
            processing_time=db_document.processing_time,
            status=status,
            metadata=db_document.metadata or {}
        )