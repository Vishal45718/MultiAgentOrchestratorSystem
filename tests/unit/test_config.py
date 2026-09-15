"""Unit tests for application configuration."""

import pytest

from src.config import Settings, get_settings


def test_default_settings_without_secrets():
    """Verify safe default settings can be loaded without requiring real secrets."""
    settings = Settings()

    assert settings.ENVIRONMENT == "development"
    assert settings.APP_NAME == "MultiAgentOrchestrationSystem"
    assert settings.DEBUG is False
    assert settings.LOG_LEVEL == "INFO"

    # Ports
    assert settings.API_PORT == 8000
    assert settings.STREAMLIT_PORT == 8501

    # Database
    assert settings.POSTGRES_USER == "postgres"
    assert settings.POSTGRES_PASSWORD == "postgres"
    assert settings.POSTGRES_HOST == "localhost"
    assert settings.POSTGRES_PORT == 5432
    assert settings.POSTGRES_DB == "orchestrator"
    assert (
        settings.sync_database_url
        == "postgresql://postgres:postgres@localhost:5432/orchestrator"
    )
    assert (
        settings.async_database_url
        == "postgresql+asyncpg://postgres:postgres@localhost:5432/orchestrator"
    )

    # Redis
    assert settings.REDIS_HOST == "localhost"
    assert settings.REDIS_PORT == 6379
    assert settings.REDIS_PASSWORD is None
    assert settings.REDIS_DB == 0
    assert settings.redis_connection_url == "redis://localhost:6379/0"

    # Celery fallback to Redis
    assert settings.effective_celery_broker_url == "redis://localhost:6379/0"
    assert settings.effective_celery_result_backend == "redis://localhost:6379/0"

    # ChromaDB
    assert settings.CHROMA_HOST == "localhost"
    assert settings.CHROMA_PORT == 8000

    # LLM keys optional
    assert settings.OPENAI_API_KEY is None
    assert settings.ANTHROPIC_API_KEY is None
    assert settings.OPENAI_MODEL == "gpt-4o"
    assert settings.ANTHROPIC_MODEL == "claude-3-5-sonnet-20241022"


def test_settings_from_environment_variables(monkeypatch: pytest.MonkeyPatch):
    """Verify settings are overridden by environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("POSTGRES_DB", "test_db")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("REDIS_PASSWORD", "secretredis")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-mock")

    settings = Settings()

    assert settings.ENVIRONMENT == "testing"
    assert settings.POSTGRES_DB == "test_db"
    assert settings.POSTGRES_PORT == 5433
    assert (
        settings.sync_database_url
        == "postgresql://postgres:postgres@localhost:5433/test_db"
    )
    assert settings.REDIS_PASSWORD == "secretredis"
    assert settings.redis_connection_url == "redis://:secretredis@localhost:6379/0"
    assert settings.OPENAI_API_KEY == "test-key-mock"


def test_settings_url_overrides(monkeypatch: pytest.MonkeyPatch):
    """Verify explicit URL overrides take precedence."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@custom:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://custom:6379/1")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/2")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://backend:6379/3")

    settings = Settings()

    assert settings.sync_database_url == "postgresql://user:pass@custom:5432/db"
    assert settings.async_database_url == "postgresql://user:pass@custom:5432/db"
    assert settings.redis_connection_url == "redis://custom:6379/1"
    assert settings.effective_celery_broker_url == "redis://broker:6379/2"
    assert settings.effective_celery_result_backend == "redis://backend:6379/3"


def test_get_settings_cached():
    """Verify get_settings returns a Settings instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert isinstance(s1, Settings)
    assert s1 is s2
