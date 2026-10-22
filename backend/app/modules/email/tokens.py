"""Signed tokens for one-click unsubscribe links.

Same construction as the OAuth-state tokens: a short-lived JWT signed with the
app secret carrying the recipient's scope, id, and email. Verification checks
that the token is genuine, so a recipient cannot unsubscribe anyone but
themselves.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

_TOKEN_TYPE = "unsubscribe"
_UNSUBSCRIBE_TTL = timedelta(days=90)


def create_unsubscribe_token(*, scope: str, object_id: uuid.UUID | str, email: str) -> str:
    """Mint an unsubscribe token for a waitlist entry (``scope="waitlist"``) or user (``scope="user"``)."""
    payload = {
        "sub": str(object_id),
        "email": email,
        "scope": scope,
        "type": _TOKEN_TYPE,
        "exp": datetime.now(timezone.utc) + _UNSUBSCRIBE_TTL,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_unsubscribe_token(token: str) -> dict | None:
    """Return the token payload, or ``None`` if invalid/expired/forged."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

    if payload.get("type") != _TOKEN_TYPE or not payload.get("sub") or not payload.get("email"):
        return None
    return payload
