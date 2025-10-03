"""
Core module for UTESCA Portal Backend.

This module provides configuration, database connections, and shared utilities.
"""

from .config import get_settings, settings
from .database import get_supabase_client, get_schema

__all__ = [
    "get_settings",
    "settings",
    "get_supabase_client",
    "get_schema",
]
