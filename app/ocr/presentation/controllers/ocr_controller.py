from fastapi import APIRouter, UploadFile, File, HTTPException
from app.ocr.application.ocr_service import OCRService
from app.ocr.presentation.schemas.ocr_schemas import OCRResponse


class OCRController:
    def __init__(self):
        self.router = APIRouter(prefix="/ocr", tags=["OCR"])
        self.ocr_service = OCRService()
        self._register_routes()

    def _register_routes(self):
        @self.router.post("/extract", response_model=OCRResponse)
        async def extract_text(file: UploadFile = File(...)):
            """
            이미지 파일을 업로드하여 텍스트를 추출합니다.
            """
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

            result = await self.ocr_service.process_image(file)
            return OCRResponse(**result)