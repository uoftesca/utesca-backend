"""
Email service module for transactional emails.
"""

from .models import EmailRecipient, EmailSendResult
from .service import EmailService

__all__ = ["EmailService", "EmailRecipient", "EmailSendResult"]
