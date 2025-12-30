"""
Models for email-related data structures.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr


class EmailRecipient(BaseModel):
    """Recipient information for sending emails."""

    email: EmailStr
    name: Optional[str] = None


class EmailSendResult(BaseModel):
    """Result of an email send operation."""

    success: bool
    recipient: str
    error: Optional[str] = None
