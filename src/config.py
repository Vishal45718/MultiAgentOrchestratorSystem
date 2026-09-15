"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration settings for the Multi-Agent Orchestration System."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application / Environment
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    APP_NAME: str = Field(
        default="MultiAgentOrchestrationSystem", description="Application name"
    )
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Log level")

    # Service Ports & Hosts
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    STREAMLIT_PORT: int = Field(default=8501, description="Streamlit UI port")

    # PostgreSQL Connection
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL user")
    POSTGRES_PASSWORD: str = Field(
        default="postgres", description="PostgreSQL password"
    )
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_DB: str = Field(
        default="orchestrator", description="PostgreSQL database name"
    )
    DATABASE_URL: Optional[str] = Field(
        default=None, description="Direct Database URL override"
    )

    @property
    def sync_database_url(self) -> str:
        """Construct synchronous database URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        """Construct asynchronous database URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis Connection
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    REDIS_DB: int = Field(default=0, description="Redis DB index")
    REDIS_URL: Optional[str] = Field(
        default=None, description="Direct Redis URL override"
    )

    @property
    def redis_connection_url(self) -> str:
        """Construct Redis connection URL."""
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Celery
    CELERY_BROKER_URL: Optional[str] = Field(
        default=None, description="Celery broker URL override"
    )
    CELERY_RESULT_BACKEND: Optional[str] = Field(
        default=None, description="Celery result backend URL override"
    )

    @property
    def effective_celery_broker_url(self) -> str:
        """Effective Celery broker URL defaulting to Redis connection URL."""
        return self.CELERY_BROKER_URL or self.redis_connection_url

    @property
    def effective_celery_result_backend(self) -> str:
        """Effective Celery result backend URL defaulting to Redis connection URL."""
        return self.CELERY_RESULT_BACKEND or self.redis_connection_url

    # ChromaDB Connection
    CHROMA_HOST: str = Field(default="localhost", description="ChromaDB host")
    CHROMA_PORT: int = Field(default=8000, description="ChromaDB port")
    CHROMA_PERSIST_DIR: Optional[str] = Field(
        default=None, description="ChromaDB persistence directory"
    )

    # LLM Provider Configuration
    OPENAI_API_KEY: Optional[str] = Field(
        default=None, description="OpenAI API key (optional for safe testing)"
    )
    OPENAI_MODEL: str = Field(default="gpt-4o", description="Default OpenAI model")
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None, description="Anthropic API key (optional for safe testing)"
    )
    ANTHROPIC_MODEL: str = Field(
        default="claude-3-5-sonnet-20241022", description="Default Anthropic model"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()


settings = get_settings()
