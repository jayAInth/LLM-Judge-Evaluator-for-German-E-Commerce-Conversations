"""
Application Configuration

Centralized configuration management using Pydantic settings
with environment variable support.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "LLM Judge Framework"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")

    # API
    API_V1_PREFIX: str = "/api/v1"
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)

    # Security
    SECRET_KEY: str = Field(default="change-me-in-production-use-secrets-manager")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)  # 24 hours
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://llmjudge:llmjudge@localhost:5432/llmjudge"
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_CACHE_TTL: int = Field(default=3600)  # 1 hour

    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")
    CELERY_TASK_TIME_LIMIT: int = Field(default=3600)  # 1 hour max per task

    # LLM Judge
    JUDGE_MODEL_PROVIDER: str = Field(default="openai_compatible")
    JUDGE_MODEL_NAME: str = Field(default="gpt-oss-120b")
    JUDGE_API_URL: str = Field(default="http://localhost:8080/v1")
    JUDGE_API_KEY: str = Field(default="not-needed")
    JUDGE_TEMPERATURE: float = Field(default=0.1)
    JUDGE_MAX_TOKENS: int = Field(default=4096)
    JUDGE_TIMEOUT: float = Field(default=120.0)

    # LanguageTool
    LANGUAGETOOL_URL: str = Field(default="http://localhost:8081/v2")
    LANGUAGETOOL_ENABLED: bool = Field(default=True)

    # Batch Processing
    BATCH_SIZE_DEFAULT: int = Field(default=100)
    BATCH_SIZE_MAX: int = Field(default=1000)
    BATCH_CONCURRENCY: int = Field(default=5)

    # Storage
    STORAGE_TYPE: str = Field(default="local")  # local, s3, minio
    STORAGE_PATH: str = Field(default="./data")
    S3_BUCKET: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None

    # GDPR / Compliance
    AUDIT_LOG_ENABLED: bool = Field(default=True)
    DATA_RETENTION_DAYS: int = Field(default=365)
    PII_REDACTION_ENABLED: bool = Field(default=True)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()
