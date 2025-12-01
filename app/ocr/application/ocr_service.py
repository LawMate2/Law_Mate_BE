from typing import Dict, Any
from fastapi import UploadFile

from app.ocr.infrastructure.clova_ocr_client import ClovaOCRClient
from app.ocr.application.text_analysis_service import TextAnalysisService


class OCRService:
    def __init__(self, text_analysis_service: TextAnalysisService = None):
        # 나중에 Google Vision 등으로 교체 시 여기만 수정하거나 DI를 사용하면 됨
        self.ocr_client = ClovaOCRClient()
        self.text_analysis_service = text_analysis_service

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

    async def analyze_text(self, text: str, questions=None) -> Dict[str, Any]:
        """
        OCR 텍스트를 AI로 분석하여 주의사항 제공

        Args:
            text: OCR로 추출된 텍스트

        Returns:
            Dict: 분석 결과
        """
        if not self.text_analysis_service:
            raise ValueError("Text analysis service is not configured")

        return await self.text_analysis_service.analyze_text(text, questions=questions or [])
