from pydantic import BaseModel

class OCRResponse(BaseModel):
    filename: str
    text: str
    provider: str