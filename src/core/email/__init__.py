"""
Email service module for transactional emails.
"""

from .service import EmailService
from .models import EmailRecipient, EmailSendResult

__all__ = ["EmailService", "EmailRecipient", "EmailSendResult"]
