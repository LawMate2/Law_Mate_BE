from typing import Optional
from pydantic import BaseModel


class DocumentUploadRequest(BaseModel):
    filename: str
    file_size: int


class DocumentResponse(BaseModel):
    success: bool
    message: str
    document_id: Optional[str] = None