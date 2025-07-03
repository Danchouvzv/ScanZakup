"""
Application configuration using Pydantic Settings.

FAANG-grade configuration management with type safety and validation.
"""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import BaseSettings, AnyHttpUrl, validator, Field
import secrets


class Settings(BaseSettings):
    """Application settings with type validation."""
    
    # Application
    APP_NAME: str = "ScanZakup API"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "scanzakup"
    DATABASE_USER: str = "scanzakup"
    DATABASE_PASSWORD: str = "password"
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        """Assemble database URL if not provided."""
        if isinstance(v, str) and v:
            return v
        return (
            f"postgresql://{values.get('DATABASE_USER')}:"
            f"{values.get('DATABASE_PASSWORD')}@"
            f"{values.get('DATABASE_HOST')}:"
            f"{values.get('DATABASE_PORT')}/"
            f"{values.get('DATABASE_NAME')}"
        )
    
    # Goszakup API
    GOSZAKUP_API_TOKEN: str = Field(..., env="GOSZAKUP_API_TOKEN")
    GOSZAKUP_API_BASE_URL: str = "https://ows.goszakup.gov.kz/v2"
    GOSZAKUP_GRAPHQL_URL: str = "https://ows.goszakup.gov.kz/v3/graphql"
    GOSZAKUP_RATE_LIMIT: int = 5  # requests per second
    GOSZAKUP_TIMEOUT: int = 30  # seconds
    GOSZAKUP_MAX_RETRIES: int = 3
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "Asia/Almaty"
    CELERY_TASK_ROUTES: dict = {
        "app.ingest_workers.tasks.sync_trd_buy": {"queue": "ingest"},
        "app.ingest_workers.tasks.sync_delta": {"queue": "ingest"},
        "app.ingest_workers.tasks.sync_contracts": {"queue": "ingest"},
    }
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[Union[str, AnyHttpUrl]] = [
        "http://localhost:3000",
        "https://localhost:3000",
        "http://localhost",
        "https://localhost",
    ]
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Parse CORS origins from environment variable."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Monitoring and Observability
    PROMETHEUS_METRICS_PATH: str = "/metrics"
    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None
    
    # File Storage
    UPLOAD_PATH: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_FILE_EXTENSIONS: List[str] = [".xlsx", ".csv", ".json"]
    
    # Excel Export
    MAX_EXPORT_ROWS: int = 100000
    EXPORT_TIMEOUT_SECONDS: int = 300
    EXPORT_CHUNK_SIZE: int = 1000
    
    # Security Headers
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # Feature Flags
    ENABLE_GRAPHQL: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_RATE_LIMITING: bool = True
    
    # Cache Settings
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 1000
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 100
    
    # Background Tasks
    INGEST_SCHEDULE_MINUTES: int = 30
    CLEANUP_SCHEDULE_HOURS: int = 24
    BACKUP_SCHEDULE_HOURS: int = 6
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings() 