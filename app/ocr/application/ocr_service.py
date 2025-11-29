from fastapi import UploadFile
from app.ocr.infrastructure.clova_ocr_client import ClovaOCRClient


# from app.ocr.presentation.schemas.ocr_schemas import OCRExtractResponse (순환 참조 주의: 아래에서 정의)

class OCRService:
    def __init__(self):
        # 나중에 Google Vision 등으로 교체 시 여기만 수정하거나 DI를 사용하면 됨
        self.ocr_client = ClovaOCRClient()

    async def process_image(self, file: UploadFile) -> dict:
        """이미지를 받아 텍스트를 추출하는 유즈케이스"""

        # 1. 텍스트 추출
        extracted_text = await self.ocr_client.extract_text(file)

        # 2. (선택사항) 결과 후처리 로직 (예: 개인정보 마스킹 등)

        return {
            "filename": file.filename,
            "text": extracted_text,
            "provider": "CLOVA"
        }