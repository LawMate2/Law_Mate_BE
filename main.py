from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import create_tables
from app.presentation.controllers.chat_controller import ChatController
from app.presentation.controllers.document_controller import DocumentController

# FastAPI 앱 생성
app = FastAPI(
    title="DDD RAG Chatbot API",
    description="Domain-Driven Design으로 구현한 LangGraph RAG 챗봇 서비스",
    version="2.0.0"
)

# 데이터베이스 테이블 초기화
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    try:
        create_tables()
        print("✅ 데이터베이스 테이블이 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"❌ 데이터베이스 테이블 생성 중 오류 발생: {e}")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 컨트롤러 등록
chat_controller = ChatController()
document_controller = DocumentController()

app.include_router(chat_controller.router)
app.include_router(document_controller.router)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "DDD RAG Chatbot API",
        "version": "2.0.0",
        "architecture": "Domain-Driven Design",
        "features": [
            "FAISS Vector Store",
            "OpenAI Embeddings",
            "MySQL RDS",
            "MLflow Tracking",
            "Clean Architecture"
        ],
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "service": "ddd-rag-chatbot-api",
        "version": "2.0.0"
    }


@app.get("/architecture")
async def architecture_info():
    """아키텍처 정보"""
    return {
        "architecture": "Domain-Driven Design (DDD)",
        "layers": {
            "domain": {
                "entities": ["Document", "ChatSession", "ChatMessage", "SearchResult"],
                "value_objects": ["DocumentChunk", "EmbeddingResult", "PerformanceMetrics"],
                "repositories": ["DocumentRepository", "ChatSessionRepository", "ChatMessageRepository", "VectorStoreRepository"]
            },
            "application": {
                "use_cases": ["DocumentUseCases", "ChatUseCases", "SearchUseCases"],
                "services": ["DocumentProcessor", "LLMService", "MLflowTracker"]
            },
            "infrastructure": {
                "repositories": ["SqlAlchemyRepositories", "FAISSVectorStoreRepository"],
                "services": ["OpenAILLMService", "StandardMLflowTracker"]
            },
            "presentation": {
                "controllers": ["ChatController", "DocumentController"],
                "schemas": ["Request/Response DTOs"]
            }
        },
        "benefits": [
            "관심사 분리",
            "테스트 용이성",
            "유지보수성 향상",
            "비즈니스 로직 독립성",
            "확장성"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)