"""Signed, short-lived OAuth ``state`` tokens shared by all providers.

The token guards against login CSRF and also carries the intent of the flow
(``login`` vs connecting a data provider) plus, for connect flows, the
authenticated user the connection must be attached to.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# Kept short: state is a CSRF guard, not a session.
OAUTH_STATE_TTL_MINUTES = 10


def create_oauth_state(flow: str, user_id: str | None = None) -> str:
    """Generate a signed random state token scoped to ``flow`` (and optionally a user)."""
    now = datetime.now(timezone.utc)
    payload = {
        "type": "oauth_state",
        "flow": flow,
        "nonce": secrets.token_urlsafe(24),
        "iat": now,
        "exp": now + timedelta(minutes=OAUTH_STATE_TTL_MINUTES),
    }
    if user_id is not None:
        payload["sub"] = str(user_id)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_oauth_state(state: str | None, expected_flow: str) -> dict | None:
    """Return the decoded payload if ``state`` is valid and matches ``expected_flow``."""
    if not state:
        return None
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "oauth_state" or payload.get("flow") != expected_flow:
        return None
    return payload
