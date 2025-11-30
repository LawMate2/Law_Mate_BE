import httpx
import json
import uuid
import time
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.ocr.domain.ocr_client import OCRClient  # 인터페이스 상속


class ClovaOCRClient(OCRClient):
    def __init__(self):
        self.api_url = settings.CLOVA_OCR_API_URL
        self.secret_key = settings.CLOVA_OCR_SECRET_KEY

    async def extract_text(self, file: UploadFile) -> str:
        if not self.api_url or not self.secret_key:
            raise HTTPException(status_code=500, detail="OCR 설정이 누락되었습니다.")

        content = await file.read()
        file_ext = file.filename.split('.')[-1].lower()

        request_json = {
            "images": [{
                "format": file_ext if file_ext in ['jpg', 'png', 'pdf'] else 'jpg',
                "name": "uploaded_doc",
                "data": None
            }],
            "requestId": str(uuid.uuid4()),
            "version": "V2",
            "timestamp": int(round(time.time() * 1000))
        }

        files = {'file': (file.filename, content, file.content_type)}
        data = {'message': json.dumps(request_json)}
        headers = {'X-OCR-SECRET': self.secret_key}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.api_url, headers=headers, data=data, files=files, timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return self._parse_response(result)
            except Exception as e:
                print(f"❌ OCR 요청 실패: {e}")
                raise HTTPException(status_code=502, detail="OCR 처리 실패")
            finally:
                await file.seek(0)

    def _parse_response(self, response: dict) -> str:
        texts = []
        for image in response.get("images", []):
            for field in image.get("fields", []):
                texts.append(field.get("inferText", ""))
        return " ".join(texts)