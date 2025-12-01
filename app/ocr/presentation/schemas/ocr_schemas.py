from typing import List, Optional
from pydantic import BaseModel, Field


class OCRResponse(BaseModel):
    filename: str
    text: str
    provider: str


class OCRAnalysisRequest(BaseModel):
    """OCR 텍스트 분석 요청"""
    text: str = Field(..., min_length=1, description="분석할 텍스트")
    questions: List[str] = Field(default_factory=list, description="추가로 답변을 원하는 질문 목록")


class KeyPoint(BaseModel):
    """주요 포인트"""
    title: str = Field(..., description="주의사항 제목")
    description: str = Field(..., description="주의사항 상세 설명")
    importance: str = Field(..., description="중요도 (high, medium, low)")


class QAItem(BaseModel):
    """질문-답변 페어"""
    question: str = Field(..., description="사용자 질문")
    answer: str = Field(..., description="문서 내용 기반 답변")


class OCRAnalysisResponse(BaseModel):
    """OCR 텍스트 분석 응답"""
    summary: str = Field(..., description="문서 요약")
    document_type: str = Field(..., description="문서 유형 (예: 계약서, 고지서, 영수증 등)")
    key_points: List[KeyPoint] = Field(..., description="주의할 점 목록")
    recommendations: List[str] = Field(..., description="권장사항 목록")
    qa: List[QAItem] = Field(default_factory=list, description="질문-답변 목록")
