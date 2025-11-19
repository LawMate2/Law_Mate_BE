import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.documents.application.use_cases.document_use_cases import DocumentUseCases
from app.documents.presentation.schemas.document_schemas import DocumentResponse
from app.shared.dependencies import get_document_use_cases


class DocumentController:
    """문서 컨트롤러"""

    def __init__(self):
        self.router = APIRouter(prefix="/documents", tags=["documents"])
        self._register_routes()

    def _register_routes(self):
        """라우트 등록"""

        @self.router.post("/upload", response_model=DocumentResponse)
        async def upload_document(
            file: UploadFile = File(...),
            document_use_cases: DocumentUseCases = Depends(get_document_use_cases),
            db: Session = Depends(get_db)
        ):
            """문서 업로드"""
            try:
                # 지원되는 파일 형식 확인
                allowed_extensions = ['.pdf', '.txt', '.docx']
                file_extension = os.path.splitext(file.filename)[1].lower()

                if file_extension not in allowed_extensions:
                    raise HTTPException(
                        status_code=400,
                        detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_extensions)}"
                    )

                # 업로드 디렉토리 생성
                os.makedirs(settings.upload_dir, exist_ok=True)

                # 파일 저장
                file_path = os.path.join(settings.upload_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                # 파일 정보 가져오기
                file_size = os.path.getsize(file_path)

                # 문서 업로드 처리
                document = await document_use_cases.upload_document(
                    filename=file.filename,
                    file_path=file_path,
                    file_size=file_size,
                    file_type=file_extension
                )

                return DocumentResponse(
                    success=True,
                    message="문서가 성공적으로 업로드되고 처리되었습니다.",
                    document_id=str(document.id)
                )

            except ValueError as e:
                # 파일 삭제
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                # 파일 삭제
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류: {str(e)}")

        @self.router.get("/")
        async def list_documents(
            skip: int = 0,
            limit: int = 100,
            document_use_cases: DocumentUseCases = Depends(get_document_use_cases)
        ):
            """문서 목록 조회"""
            try:
                documents = await document_use_cases.list_documents(skip, limit)
                return [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "file_size": doc.file_size,
                        "file_type": doc.file_type,
                        "upload_time": doc.upload_time,
                        "chunk_count": doc.chunk_count,
                        "status": doc.status.value,
                        "processing_time": doc.processing_time
                    }
                    for doc in documents
                ]
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"문서 목록 조회 중 오류: {str(e)}")

        @self.router.get("/{document_id}")
        async def get_document(
            document_id: int,
            document_use_cases: DocumentUseCases = Depends(get_document_use_cases)
        ):
            """문서 상세 조회"""
            try:
                document = await document_use_cases.get_document_by_id(document_id)
                if not document:
                    raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

                return {
                    "id": document.id,
                    "filename": document.filename,
                    "file_path": document.file_path,
                    "file_size": document.file_size,
                    "file_type": document.file_type,
                    "upload_time": document.upload_time,
                    "chunk_count": document.chunk_count,
                    "status": document.status.value,
                    "processing_time": document.processing_time,
                    "metadata": document.metadata
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"문서 조회 중 오류: {str(e)}")

        @self.router.delete("/{document_id}", response_model=DocumentResponse)
        async def delete_document(
            document_id: int,
            document_use_cases: DocumentUseCases = Depends(get_document_use_cases)
        ):
            """문서 삭제"""
            try:
                success = await document_use_cases.delete_document(document_id)

                if success:
                    return DocumentResponse(
                        success=True,
                        message="문서가 성공적으로 삭제되었습니다."
                    )
                else:
                    raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"문서 삭제 중 오류: {str(e)}")

        @self.router.get("/statistics/overview")
        async def get_document_statistics(
            document_use_cases: DocumentUseCases = Depends(get_document_use_cases)
        ):
            """문서 통계"""
            try:
                return await document_use_cases.get_document_statistics()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"통계 조회 중 오류: {str(e)}")
