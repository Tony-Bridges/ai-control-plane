# src/core/config.py
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "AI Control Plane"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    
    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "ai_control_plane"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Control Plane"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"  # Keep this to catch missing fields
    )

# Create a singleton instance
settings = Settings()