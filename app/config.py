
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Contract Processing System"
    APP_ENV: str = "development"
    DEBUG: bool = True

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    DATABASE_URL: str
    RABBITMQ_URL: str

    STORAGE_PATH: str = "storage/uploads"
    TEMP_PATH: str = "storage/temp"

    MAX_DOCUMENTS_PER_BATCH: int = 1000
    MAX_DOCUMENT_SIZE_MB: int = 15

    RABBITMQ_QUEUE: str = "document_processing"
    RABBITMQ_DLQ: str = "document_processing_dlq"

    WORKER_CONCURRENCY: int = 5
    MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
