from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
import os

from app.auth.presentation.controllers.auth_controller import AuthController
from app.chat.presentation.controllers.chat_controller import ChatController
from app.documents.presentation.controllers.document_controller import DocumentController
from app.db.database import create_tables

# ========================
# FastAPI 앱 생성
# ========================
app = FastAPI(
    title="DDD RAG Chatbot API",
    description="Domain-Driven Design으로 구현한 LangGraph RAG 챗봇 서비스",
    version="2.0.0"
)

# ========================
# CORS 설정
# ========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# 서버 시작 시 DB 초기화
# ========================
@app.on_event("startup")
async def startup_event():
    try:
        create_tables()
        print("✅ 데이터베이스 테이블 생성 완료")
    except Exception as e:
        print(f"❌ DB 초기화 실패: {e}")

# ========================
# 컨트롤러 등록
# ========================
app.include_router(ChatController().router)
app.include_router(DocumentController().router)
app.include_router(AuthController().router)

# ========================
# 기본 엔드포인트
# ========================
@app.get("/")
async def root():
    return {"status": "DDD RAG API Running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# ========================
# PDF 업로드 & 파싱 API
# ========================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def extract_text_from_pdf(path: str) -> str:
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


from uuid import uuid4
from pydantic import BaseModel

class UploadPDFResponse(BaseModel):
    success: bool
    message: str
    document_id: str


@app.post("/upload-pdf", response_model=UploadPDFResponse)
async def upload_pdf(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    extracted_text = extract_text_from_pdf(file_path)

    # 여기가 나중에 DB에 저장될 위치
    document_id = str(uuid4())

    return UploadPDFResponse(
        success=True,
        message="PDF 업로드 및 파싱 완료",
        document_id=document_id
    )
