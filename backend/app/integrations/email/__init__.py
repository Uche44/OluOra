"""Email provider implementations and the factory that resolves the active one.

Import :func:`get_email_provider` — never a concrete provider — so the vendor
stays a configuration detail (``EMAIL_PROVIDER``).
"""

from app.integrations.email.base import EmailProvider, OutboundEmail, SendResult
from app.integrations.email.factory import get_email_provider

__all__ = [
    "EmailProvider",
    "OutboundEmail",
    "SendResult",
    "get_email_provider",
]
