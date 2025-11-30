from abc import ABC, abstractmethod
from fastapi import UploadFile


class OCRClient(ABC):
    """OCR 기능을 수행하는 클라이언트의 추상 인터페이스"""

    @abstractmethod
    async def extract_text(self, file: UploadFile) -> str:
        pass