from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    """회원 테이블"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))
    given_name = Column(String(255))
    family_name = Column(String(255))
    picture = Column(String(500))
    locale = Column(String(50))
    verified_email = Column(Boolean, default=False)
    access_token = Column(Text)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    metadata = Column(JSON)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class Document(Base):
    """문서 테이블"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    chunk_count = Column(Integer, default=0)
    processing_time = Column(Float)
    is_processed = Column(Boolean, default=False)
    metadata = Column(JSON)

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}')>"


class ChatSession(Base):
    """채팅 세션 테이블"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    total_messages = Column(Integer, default=0)
    metadata = Column(JSON)

    def __repr__(self):
        return f"<ChatSession(id={self.id}, session_id='{self.session_id}')>"


class ChatMessage(Base):
    """채팅 메시지 테이블"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # 성능 메트릭
    retrieve_time = Column(Float)
    generate_time = Column(Float)
    total_time = Column(Float)
    context_length = Column(Integer)
    response_length = Column(Integer)

    # 검색 관련 메트릭
    similarity_scores = Column(JSON)  # 유사도 점수들
    retrieved_chunks = Column(Integer)  # 검색된 청크 수

    metadata = Column(JSON)

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role='{self.role}', session_id='{self.session_id}')>"


class MLflowRun(Base):
    """MLflow 실행 추적 테이블"""
    __tablename__ = "mlflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(100), unique=True, index=True)
    run_name = Column(String(255))
    experiment_name = Column(String(255))
    status = Column(String(20))  # RUNNING, FINISHED, FAILED
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    duration = Column(Float)

    # 메트릭
    metrics = Column(JSON)
    parameters = Column(JSON)
    tags = Column(JSON)

    # 연관 정보
    session_id = Column(String(100), index=True)
    document_id = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<MLflowRun(id={self.id}, run_id='{self.run_id}', status='{self.status}')>"


class SystemMetrics(Base):
    """시스템 메트릭 테이블"""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # 시스템 상태
    total_documents = Column(Integer)
    total_chunks = Column(Integer)
    total_chat_sessions = Column(Integer)
    total_messages = Column(Integer)

    # 성능 메트릭
    avg_response_time = Column(Float)
    avg_retrieve_time = Column(Float)
    avg_generate_time = Column(Float)

    # 품질 메트릭
    avg_similarity_score = Column(Float)
    success_rate = Column(Float)

    metadata = Column(JSON)

    def __repr__(self):
        return f"<SystemMetrics(id={self.id}, timestamp='{self.timestamp}')>"
