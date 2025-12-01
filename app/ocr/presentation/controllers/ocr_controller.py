from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.ocr.application.ocr_service import OCRService
from app.ocr.presentation.schemas.ocr_schemas import (
    OCRResponse,
    OCRAnalysisRequest,
    OCRAnalysisResponse,
    KeyPoint
)
from app.shared.dependencies import get_ocr_service


class OCRController:
    def __init__(self):
        self.router = APIRouter(prefix="/ocr", tags=["OCR"])
        self._register_routes()

    def _register_routes(self):
        @self.router.post("/extract", response_model=OCRResponse)
        async def extract_text(
            file: UploadFile = File(...),
            ocr_service: OCRService = Depends(get_ocr_service)
        ):
            """
            이미지 파일을 업로드하여 텍스트를 추출합니다.
            """
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

            result = await ocr_service.process_image(file)
            return OCRResponse(**result)

        @self.router.post("/analyze", response_model=OCRAnalysisResponse)
        async def analyze_text(
            request: OCRAnalysisRequest,
            ocr_service: OCRService = Depends(get_ocr_service)
        ):
            """
            OCR로 추출된 텍스트를 AI로 분석하여 주의사항을 제공합니다.
            """
            try:
                result = await ocr_service.analyze_text(request.text, questions=request.questions)

                # KeyPoint 객체로 변환
                key_points = [
                    KeyPoint(**kp) for kp in result.get("key_points", [])
                ]
                qa_items = result.get("qa", []) or []

                return OCRAnalysisResponse(
                    summary=result.get("summary", ""),
                    document_type=result.get("document_type", ""),
                    key_points=key_points,
                    recommendations=result.get("recommendations", []),
                    qa=qa_items
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"텍스트 분석 중 오류: {str(e)}")
