# ============================================================================
# MARKETMIND AI - SETTINGS & ENVIRONMENT SYSTEM
# ============================================================================

from typing import Literal, Optional, List, Any
from pydantic import Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # General App Settings
    APP_NAME: str = "MarketMind AI"
    ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security & Tokens
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # PostgreSQL Database URL
    DATABASE_URL: str

    # Supabase Credentials (required for platform services)
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str

    # NVIDIA NIM Configurations
    NVIDIA_API_KEY: str
    NVIDIA_NIM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_LLM_MODEL: str = "nvidia/llama-3.1-instruct-70b"

    # Research Run Timeout configuration (seconds)
    RESEARCH_RUN_TIMEOUT_SECONDS: int = 300

    # Redis Configurations
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL_NEWS: int = 14400      # 4 hours
    REDIS_CACHE_TTL_PRICES: int = 86400    # 24 hours
    REDIS_CACHE_TTL_REPORTS: int = 86400   # 24 hours
    RESEARCH_LOCK_TTL_SECONDS: int = 180   # 3 minutes lock expiry

    # Vector Embeddings
    EMBEDDING_PROVIDER: Literal["openai", "local", "nim"] = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    OPENAI_API_KEY: Optional[str] = None

    # CORS Configurations
    ALLOWED_ORIGINS: Any = ["*"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    import json
                    parsed = json.loads(v_stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENV == "production":
            if "*" in self.ALLOWED_ORIGINS:
                raise ValueError("Wildcard CORS origins ('*') are not allowed in production environment.")
            if not self.DATABASE_URL:
                raise ValueError("DATABASE_URL must be configured in production environment.")
            if not (self.DATABASE_URL.startswith("postgresql://") or self.DATABASE_URL.startswith("postgresql+asyncpg://")):
                raise ValueError("PostgreSQL database URL is required in production environment. SQLite is not allowed.")
        return self


settings = Settings()

