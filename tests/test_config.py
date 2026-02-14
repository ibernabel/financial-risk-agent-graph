"""
Unit tests for core configuration module.
"""

import pytest
from app.core.config import Settings, DatabaseSettings, LLMSettings, APISettings


def test_settings_load_defaults():
    """Test that settings load with default values."""
    settings = Settings()

    assert settings.api.name == "CreditGraph AI"
    assert settings.api.version == "0.1.0"
    assert settings.api.port == 8000
    assert settings.llm.default_provider in ["anthropic", "openai", "google"]


def test_database_settings():
    """Test database settings configuration."""
    db_settings = DatabaseSettings()

    assert db_settings.pool_size == 10
    assert db_settings.max_overflow == 20
    assert db_settings.pool_timeout == 30


def test_llm_settings():
    """Test LLM provider settings."""
    llm_settings = LLMSettings()

    assert llm_settings.anthropic_model == "claude-3-5-sonnet-20241022"
    assert llm_settings.openai_model == "gpt-4o"
    assert llm_settings.google_model == "gemini-2.0-flash-exp"
    assert llm_settings.temperature == 0.1
    assert llm_settings.max_tokens == 4096


def test_api_settings():
    """Test API configuration."""
    api_settings = APISettings()

    assert api_settings.host == "0.0.0.0"
    assert api_settings.port == 8000
    assert api_settings.debug is True
    assert api_settings.cors_allow_credentials is True
