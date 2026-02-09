"""
Configuration management using Pydantic Settings.

Loads environment variables and provides type-safe configuration for the application.
"""

from typing import Literal
from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    url: PostgresDsn = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/creditflow",
        description="PostgreSQL connection URL",
    )
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(
        default=20, description="Maximum overflow connections")
    pool_timeout: int = Field(
        default=30, description="Pool timeout in seconds")

    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class LLMSettings(BaseSettings):
    """LLM provider configuration for multi-provider support."""

    # Anthropic (Claude)
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Claude model name"
    )

    # OpenAI (GPT-4o)
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-4o", description="OpenAI model for reasoning")
    openai_vision_model: str = Field(
        default="gpt-4o", description="OpenAI model for vision/OCR")

    # Google (Gemini)
    google_api_key: str = Field(default="", description="Google API key")
    google_model: str = Field(
        default="gemini-2.0-flash-exp", description="Gemini model name")

    # Default provider
    default_provider: Literal["anthropic", "openai", "google"] = Field(
        default="anthropic", description="Default LLM provider"
    )

    # LLM parameters
    temperature: float = Field(default=0.1, description="LLM temperature")
    max_tokens: int = Field(
        default=4096, description="Maximum tokens per request")
    timeout: int = Field(
        default=60, description="LLM request timeout in seconds")

    # OCR-specific settings (using GPT-4o-mini for cost efficiency)
    ocr_llm_model: str = Field(
        default="gpt-4o-mini", description="LLM model for OCR tasks")
    ocr_temperature: float = Field(
        default=0.0, description="Temperature for OCR (deterministic)")
    ocr_max_tokens: int = Field(
        default=4096, description="Max tokens for OCR responses")

    model_config = SettingsConfigDict(env_prefix="")


class APISettings(BaseSettings):
    """FastAPI application configuration."""

    name: str = Field(default="CreditFlow AI", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment"
    )
    debug: bool = Field(default=True, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Server settings
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    reload: bool = Field(
        default=True, description="Auto-reload on code changes")

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials")

    # Security
    api_key_header: str = Field(
        default="X-API-KEY", description="API key header name")
    api_secret_key: str = Field(
        default="change-me-in-production", description="API secret key"
    )

    # Rate limiting
    rate_limit_per_minute: int = Field(
        default=60, description="Requests per minute")
    rate_limit_burst: int = Field(default=10, description="Burst allowance")

    model_config = SettingsConfigDict(env_prefix="API_")


class ExternalServicesSettings(BaseSettings):
    """External service configuration."""

    # SerpAPI for OSINT
    serpapi_key: str = Field(default="", description="SerpAPI key")

    # Credit Parser API
    credit_parser_url: str = Field(
        default="http://localhost:8001/v1/parse", description="Credit parser API URL"
    )
    credit_parser_api_key: str = Field(
        default="", description="Credit parser API key")

    # Labor Calculator
    labor_calculator_url: str = Field(
        default="https://calculo.mt.gob.do/", description="Labor calculator URL"
    )

    model_config = SettingsConfigDict(env_prefix="")


class SecuritySettings(BaseSettings):
    """Security and compliance configuration."""

    # Data retention
    data_retention_hours: int = Field(
        default=24, description="Data retention in hours")

    # PII masking
    enable_pii_masking: bool = Field(
        default=True, description="Enable PII masking")
    mask_fields: list[str] = Field(
        default=["id", "phone", "email", "account_number"],
        description="Fields to mask",
    )

    # Encryption
    encryption_key: str = Field(
        default="", description="AES-256 encryption key")

    model_config = SettingsConfigDict(env_prefix="")


class FeatureFlags(BaseSettings):
    """Feature flags for enabling/disabling functionality."""

    enable_osint: bool = Field(
        default=True, description="Enable OSINT research")
    enable_checkpointing: bool = Field(
        default=True, description="Enable checkpointing")
    enable_human_review: bool = Field(
        default=True, description="Enable human review")
    force_reanalysis: bool = Field(
        default=False, description="Force reanalysis")

    model_config = SettingsConfigDict(env_prefix="")


class Settings(BaseSettings):
    """Main application settings combining all configuration sections."""

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    api: APISettings = Field(default_factory=APISettings)
    external: ExternalServicesSettings = Field(
        default_factory=ExternalServicesSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
