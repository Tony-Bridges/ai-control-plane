# src/config.py
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
from typing import List, Optional, Dict, Any, Union

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Control Plane"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production"
    PROJECT_NAME: str = "AI Control Plane"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    
    # Database - PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "ai_control_plane"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    
    # Alternative naming
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "ai_control_plane"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    
    # Database URL
    DATABASE_URL: Optional[str] = None
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # OPA
    OPA_URL: str = "http://localhost:8181"
    
    # OpenAI
    OPENAI_ENDPOINT: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ORG_ID: Optional[str] = None
    OPENAI_TIMEOUT: int = 30
    OPENAI_MAX_RETRIES: int = 3
    DEFAULT_MODEL: str = "gpt-4"
    FALLBACK_MODEL: str = "gpt-3.5-turbo"
    
    # Anthropic
    ANTHROPIC_ENDPOINT: str = "https://api.anthropic.com/v1"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_VERSION: str = "2023-06-01"
    ANTHROPIC_TIMEOUT: int = 30
    ANTHROPIC_MAX_RETRIES: int = 3
    ANTHROPIC_DEFAULT_MODEL: str = "claude-3-opus-20240229"
    
    # Google
    GOOGLE_ENDPOINT: str = "https://generativelanguage.googleapis.com/v1"
    GOOGLE_API_KEY: Optional[str] = None
    
    # Local
    LOCAL_LLAMA_ENDPOINT: str = "http://localhost:11434/api"
    LOCAL_LLAMA_MODEL: str = "llama2"
    LOCAL_LLAMA_TIMEOUT: int = 60
    LOCAL_LLAMA_MAX_RETRIES: int = 2
    LOCAL_DEFAULT_MODEL: str = "llama2"
    
    # CORS - Use a simpler approach
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000"
    ]
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse ALLOWED_ORIGINS from string or list"""
        if isinstance(v, str):
            # Handle empty string
            if not v.strip():
                return ["http://localhost:3000", "http://localhost:8000"]
            # Split by comma and clean
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            return origins if origins else ["http://localhost:3000", "http://localhost:8000"]
        elif isinstance(v, list):
            return v
        else:
            # Default
            return ["http://localhost:3000", "http://localhost:8000"]
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_database_url(cls, v: Optional[str], info) -> Optional[str]:
        """Build DATABASE_URL from individual settings if not provided"""
        if v:
            return v
        # Build from individual settings
        data = info.data
        host = data.get("POSTGRES_HOST") or data.get("DB_HOST", "localhost")
        port = data.get("POSTGRES_PORT") or data.get("DB_PORT", "5432")
        db = data.get("POSTGRES_DB") or data.get("DB_NAME", "ai_control_plane")
        user = data.get("POSTGRES_USER") or data.get("DB_USER", "postgres")
        password = data.get("POSTGRES_PASSWORD") or data.get("DB_PASSWORD", "postgres")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

settings = Settings()