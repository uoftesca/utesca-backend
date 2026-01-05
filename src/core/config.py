"""
Application configuration management using Pydantic Settings.

This module handles environment-based configuration using PostgreSQL schemas.
A single Supabase database is used with separate 'test' and 'prod' schemas.
Environment variables are loaded from .env file in development and from system
environment in production (e.g., Vercel).
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment Variables:
    - ENVIRONMENT: 'test' or 'production' (default: 'test')
    - SUPABASE_URL: Database URL
    - SUPABASE_KEY: Database anon/service key
    - API_V1_PREFIX: API version prefix (default: '/api/v1')
    - PROJECT_NAME: Project name (default: 'UTESCA Portal')
    """

    # Environment configuration
    ENVIRONMENT: Literal["test", "production"] = "test"

    # API configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "UTESCA Portal"

    # Supabase credentials (single database with test and prod schemas)
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Base URL for email redirects
    BASE_URL: str

    # Email configuration (Resend)
    RESEND_API_KEY: str

    # CORS settings (for Next.js frontend)
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",  # Local Next.js dev
        "https://utesca.ca",       # Production frontend
        "https://www.utesca.ca",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields in .env
    )

    @property
    def db_schema(self) -> str:
        """
        Get the appropriate PostgreSQL schema based on environment.

        Returns:
            'test' for test environment
            'prod' for production environment
        """
        return "prod" if self.ENVIRONMENT == "production" else "test"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.ENVIRONMENT == "test"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once.
    This is the recommended way to access settings throughout the app.

    Usage:
        from core.config import get_settings

        settings = get_settings()
        print(settings.db_schema)  # 'test' or 'prod' based on ENVIRONMENT
    """
    return Settings()  # type: ignore[call-arg]  # BaseSettings loads from env vars


# Convenience export
settings = get_settings()
