from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    openai_api_key: str
    faiss_db_path: str = "./data/faiss"
    upload_dir: str = "./data/uploads"

    # MLflow 설정
    mlflow_tracking_uri: str = "./data/mlruns"
    mlflow_experiment_name: str = "rag-chatbot"

    # MySQL RDS 설정
    mysql_host: str = "j2p.c70uuq2mcwbq.ap-southeast-2.rds.amazonaws.com"
    mysql_port: int = 3306
    mysql_username: str = "admin"
    mysql_password: str = "inforsion00"
    mysql_database: str = "rag_chatbot"

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.mysql_username}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    class Config:
        env_file = ".env"


settings = Settings()