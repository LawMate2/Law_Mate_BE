from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class DocumentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Document:
    """문서 도메인 엔티티"""
    filename: str
    file_path: str
    file_size: int
    file_type: str
    id: Optional[int] = None
    upload_time: Optional[datetime] = None
    chunk_count: int = 0
    processing_time: float = 0.0
    status: DocumentStatus = DocumentStatus.PENDING
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_processed(self) -> bool:
        return self.status == DocumentStatus.COMPLETED

    def mark_as_processing(self):
        self.status = DocumentStatus.PROCESSING

    def mark_as_completed(self, chunk_count: int, processing_time: float):
        self.status = DocumentStatus.COMPLETED
        self.chunk_count = chunk_count
        self.processing_time = processing_time

    def mark_as_failed(self):
        self.status = DocumentStatus.FAILED

    def get_file_extension(self) -> str:
        return self.file_type.lower()

    def is_supported_format(self) -> bool:
        supported_formats = ['.pdf', '.txt', '.docx']
        return self.get_file_extension() in supported_formats