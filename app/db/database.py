from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

# 데이터베이스 엔진 생성
engine = create_engine(
    settings.database_url,
    echo=True,  # SQL 쿼리 로깅
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=3600,   # 1시간마다 연결 재생성
    pool_size=10,        # 연결 풀 크기
    max_overflow=20      # 최대 추가 연결 수
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 생성
Base = declarative_base()


def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """테이블 생성"""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """테이블 삭제"""
    Base.metadata.drop_all(bind=engine)