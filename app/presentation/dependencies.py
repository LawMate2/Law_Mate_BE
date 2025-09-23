from functools import lru_cache
from sqlalchemy.orm import Session
from fastapi import Depends

from ..core.config import settings
from ..db.database import get_db

# Repository implementations
from ..infrastructure.repositories.sqlalchemy_document_repository import SqlAlchemyDocumentRepository
from ..infrastructure.repositories.sqlalchemy_chat_session_repository import SqlAlchemyChatSessionRepository
from ..infrastructure.repositories.sqlalchemy_chat_message_repository import SqlAlchemyChatMessageRepository
from ..infrastructure.repositories.faiss_vector_store_repository import FAISSVectorStoreRepository

# Application services
from ..application.services.document_processor import LangChainDocumentProcessor
from ..application.services.llm_service import OpenAILLMService
from ..application.services.mlflow_tracker import StandardMLflowTracker

# Use cases
from ..application.use_cases.document_use_cases import DocumentUseCases
from ..application.use_cases.chat_use_cases import ChatUseCases
from ..application.use_cases.search_use_cases import SearchUseCases


@lru_cache()
def get_document_processor():
    """문서 처리기 의존성"""
    return LangChainDocumentProcessor()


@lru_cache()
def get_llm_service():
    """LLM 서비스 의존성"""
    return OpenAILLMService(api_key=settings.openai_api_key)


@lru_cache()
def get_mlflow_tracker():
    """MLflow 추적 서비스 의존성"""
    return StandardMLflowTracker(
        tracking_uri=settings.mlflow_tracking_uri,
        experiment_name=settings.mlflow_experiment_name
    )


@lru_cache()
def get_vector_store_repository():
    """벡터 저장소 의존성"""
    return FAISSVectorStoreRepository(
        faiss_db_path=settings.faiss_db_path,
        openai_api_key=settings.openai_api_key
    )


def get_document_repository(db: Session = Depends(get_db)):
    """문서 저장소 의존성"""
    return SqlAlchemyDocumentRepository(db)


def get_chat_session_repository(db: Session = Depends(get_db)):
    """채팅 세션 저장소 의존성"""
    return SqlAlchemyChatSessionRepository(db)


def get_chat_message_repository(db: Session = Depends(get_db)):
    """채팅 메시지 저장소 의존성"""
    return SqlAlchemyChatMessageRepository(db)


def get_search_use_cases(
    vector_store_repository=Depends(get_vector_store_repository),
    mlflow_tracker=Depends(get_mlflow_tracker)
):
    """검색 유스케이스 의존성"""
    return SearchUseCases(
        vector_store_repository=vector_store_repository,
        mlflow_tracker=mlflow_tracker
    )


def get_document_use_cases(
    document_repository=Depends(get_document_repository),
    vector_store_repository=Depends(get_vector_store_repository),
    document_processor=Depends(get_document_processor),
    mlflow_tracker=Depends(get_mlflow_tracker)
):
    """문서 유스케이스 의존성"""
    return DocumentUseCases(
        document_repository=document_repository,
        vector_store_repository=vector_store_repository,
        document_processor=document_processor,
        mlflow_tracker=mlflow_tracker
    )


def get_chat_use_cases(
    chat_session_repository=Depends(get_chat_session_repository),
    chat_message_repository=Depends(get_chat_message_repository),
    search_use_cases=Depends(get_search_use_cases),
    llm_service=Depends(get_llm_service),
    mlflow_tracker=Depends(get_mlflow_tracker)
):
    """채팅 유스케이스 의존성"""
    return ChatUseCases(
        chat_session_repository=chat_session_repository,
        chat_message_repository=chat_message_repository,
        search_use_cases=search_use_cases,
        llm_service=llm_service,
        mlflow_tracker=mlflow_tracker
    )