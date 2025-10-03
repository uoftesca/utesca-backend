"""
Database connection and utility functions.

This module provides utilities for connecting to Supabase and setting the
correct PostgreSQL schema (test or prod) based on the environment.
"""

from supabase import create_client, Client
from functools import lru_cache
from .config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """
    Get a cached Supabase client instance.

    Usage:
        from core.database import get_supabase_client

        supabase = get_supabase_client()
        result = supabase.table("users").select("*").execute()

    Note: Schema selection (test/prod) should be handled at the database level
    through RLS policies or by prefixing table names with the schema.
    """
    settings = get_settings()
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
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
