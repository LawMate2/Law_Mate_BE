import os
import time
from typing import List, Optional

from app.documents.application.services.document_processor import DocumentProcessor
from app.documents.domain.entities.document import Document, DocumentStatus
from app.documents.domain.repositories.document_repository import DocumentRepository
from app.search.domain.repositories.vector_store_repository import VectorStoreRepository
from app.shared.services.mlflow_tracker import MLflowTracker


class DocumentUseCases:
    """문서 관련 유스케이스"""

    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_store_repository: VectorStoreRepository,
        document_processor: DocumentProcessor,
        mlflow_tracker: MLflowTracker,
        elasticsearch_repository: Optional[VectorStoreRepository] = None
    ):
        self.document_repository = document_repository
        self.vector_store_repository = vector_store_repository
        self.elasticsearch_repository = elasticsearch_repository
        self.document_processor = document_processor
        self.mlflow_tracker = mlflow_tracker

    async def upload_document(
        self,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: str
    ) -> Document:
        """문서 업로드 및 처리 (동기)"""
        document = await self.create_pending_document(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type
        )
        return await self.process_document(document)

    async def create_pending_document(
        self,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: str
    ) -> Document:
        """문서 메타만 저장하고 처리 대기 상태로 반환"""
        document = Document(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            status=DocumentStatus.PENDING
        )

        if not document.is_supported_format():
            document.mark_as_failed()
            await self.document_repository.save(document)
            raise ValueError(f"지원하지 않는 파일 형식: {file_type}")

        document.mark_as_processing()
        return await self.document_repository.save(document)

    async def process_document(self, document: Document) -> Document:
        """저장된 문서를 실제로 처리"""
        start_time = time.time()

        try:
            run_name = f"upload_document_{document.filename}"
            with self.mlflow_tracker.start_run(run_name):
                await self.mlflow_tracker.log_params({
                    "filename": document.filename,
                    "file_size": document.file_size,
                    "file_type": document.file_type
                })

                chunks = await self.document_processor.process_document(document.file_path)

                success = await self.vector_store_repository.add_documents(chunks)

                es_success = True
                if self.elasticsearch_repository:
                    try:
                        es_success = await self.elasticsearch_repository.add_documents(chunks)
                        await self.mlflow_tracker.log_metric("elasticsearch_success", 1 if es_success else 0)
                    except Exception as e:
                        print(f"Elasticsearch 저장 중 오류 (계속 진행): {e}")
                        await self.mlflow_tracker.log_text(f"Elasticsearch 오류: {e}", "elasticsearch_error.txt")

                if success:
                    processing_time = time.time() - start_time
                    document.mark_as_completed(len(chunks), processing_time)
                    await self.mlflow_tracker.log_metrics({
                        "chunk_count": len(chunks),
                        "processing_time": processing_time,
                        "success": 1
                    })
                else:
                    document.mark_as_failed()
                    await self.mlflow_tracker.log_metric("success", 0)

                return await self.document_repository.save(document)
        except Exception as e:
            document.mark_as_failed()
            await self.document_repository.save(document)
            await self.mlflow_tracker.log_text(str(e), "error.txt")
            raise

    async def process_document_by_id(self, document_id: int) -> Document:
        """문서 ID로 조회 후 처리"""
        document = await self.document_repository.find_by_id(document_id)
        if not document:
            raise ValueError("문서를 찾을 수 없습니다.")

        if document.status == DocumentStatus.COMPLETED:
            return document

        document.mark_as_processing()
        document = await self.document_repository.save(document)
        return await self.process_document(document)

    async def get_document_by_id(self, document_id: int) -> Optional[Document]:
        """문서 ID로 조회"""
        return await self.document_repository.find_by_id(document_id)

    async def get_document_by_filename(self, filename: str) -> Optional[Document]:
        """파일명으로 문서 조회"""
        return await self.document_repository.find_by_filename(filename)

    async def list_documents(self, skip: int = 0, limit: int = 100) -> List[Document]:
        """문서 목록 조회"""
        return await self.document_repository.find_all(skip, limit)

    async def delete_document(self, document_id: int) -> bool:
        """문서 삭제"""
        document = await self.document_repository.find_by_id(document_id)
        if not document:
            return False

        try:
            # 벡터 저장소에서 삭제
            await self.vector_store_repository.delete_documents(document.filename)

            # 데이터베이스에서 삭제
            await self.document_repository.delete(document_id)

            # 실제 파일 삭제
            if os.path.exists(document.file_path):
                os.remove(document.file_path)

            return True
        except Exception:
            return False

    async def get_document_statistics(self) -> dict:
        """문서 통계"""
        total_documents = await self.document_repository.count()
        vector_count = await self.vector_store_repository.get_document_count()

        return {
            "total_documents": total_documents,
            "total_chunks": vector_count,
            "avg_chunks_per_document": vector_count / total_documents if total_documents > 0 else 0
        }
