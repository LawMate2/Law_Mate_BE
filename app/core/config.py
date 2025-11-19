from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    openai_api_key: str
    faiss_db_path: str = "./data/faiss"
    upload_dir: str = "./data/uploads"

    # MLflow 설정
    mlflow_tracking_uri: str = "./data/mlruns"
    mlflow_experiment_name: str = "rag-chatbot"

    # MySQL 설정 (Docker 기본값과 호환)
    db_driver: str = Field(
        default="mysql+pymysql",
        validation_alias=AliasChoices("DB_DRIVER", "MYSQL_DRIVER"),
    )
    db_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("DB_HOST", "MYSQL_HOST"),
    )
    db_port: int = Field(
        default=3306,
        validation_alias=AliasChoices("DB_PORT", "MYSQL_PORT"),
    )
    db_username: str = Field(
        default="appuser",
        validation_alias=AliasChoices("DB_USERNAME", "MYSQL_USERNAME"),
    )
    db_password: str = Field(
        default="apppw",
        validation_alias=AliasChoices("DB_PASSWORD", "MYSQL_PASSWORD"),
    )
    db_database: str = Field(
        default="appdb",
        validation_alias=AliasChoices("DB_DATABASE", "MYSQL_DATABASE"),
    )

    # Assembly law API
    assembly_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ASSEMBLY_API_KEY", "LAW_API_KEY")
    )
    assembly_api_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ASSEMBLY_API_URL", "LAW_API_URL")
    )
    assembly_api_query_param: str = Field(
        default="search",
        validation_alias=AliasChoices("ASSEMBLY_API_QUERY_PARAM", "LAW_API_QUERY_PARAM")
    )
    assembly_api_timeout: float = Field(
        default=10.0,
        validation_alias=AliasChoices("ASSEMBLY_API_TIMEOUT", "LAW_API_TIMEOUT")
    )

    @property
    def database_url(self) -> str:
        return (
            f"{self.db_driver}://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_database}"
        )


settings = Settings()
