"""
Application configuration settings.
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Basic app info
    PROJECT_NAME: str = "UTESCA Backend API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Backend API for UTESCA web application"

    # API settings
    API_V1_STR: str = "/api/v1"

    # CORS settings
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database settings - Supabase PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/utesca"

    # Security settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
