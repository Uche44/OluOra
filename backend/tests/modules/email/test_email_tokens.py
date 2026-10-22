import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.modules.email.tokens import create_unsubscribe_token, verify_unsubscribe_token


def test_round_trip_preserves_claims():
    object_id = uuid.uuid4()
    token = create_unsubscribe_token(
        scope="waitlist", object_id=object_id, email="Fan@Example.com"
    )
    payload = verify_unsubscribe_token(token)
    assert payload is not None
    assert payload["scope"] == "waitlist"
    assert payload["sub"] == str(object_id)
    assert payload["email"] == "Fan@Example.com"


def test_forged_signature_is_rejected():
    token = create_unsubscribe_token(scope="user", object_id=uuid.uuid4(), email="a@b.com")
    assert verify_unsubscribe_token(token + "tampered") is None


def test_wrong_token_type_is_rejected():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "a@b.com",
            "scope": "user",
            "type": "access",
            "exp": now + timedelta(minutes=5),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert verify_unsubscribe_token(token) is None


def test_expired_token_is_rejected():
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "a@b.com",
            "scope": "user",
            "type": "unsubscribe",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert verify_unsubscribe_token(token) is None
