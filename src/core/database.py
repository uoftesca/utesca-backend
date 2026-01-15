"""
Database connection and utility functions.

This module provides utilities for connecting to Supabase and setting the
correct PostgreSQL schema (test or prod) based on the environment.
"""

from functools import lru_cache

from supabase import Client, create_client

from .config import get_settings

@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()
    # Ensure this is using the SERVICE_ROLE_KEY, not the ANON_KEY
    # If your config.py uses 'supabase_service_role_key', use that here.
    client = create_client(
        settings.SUPABASE_URL, 
        settings.SUPABASE_SERVICE_ROLE_KEY 
    )
    return client

def get_schema() -> str:
    """
    Get the current database schema based on environment.

    Returns:
        'test' or 'prod'

    Usage:
        from core.database import get_schema

        schema = get_schema()  # 'test' or 'prod'
    """
    settings = get_settings()
    return settings.db_schema
