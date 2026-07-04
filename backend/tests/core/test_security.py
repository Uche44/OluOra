import pytest
import jwt
from datetime import timedelta
from app.core.security import create_access_token, create_refresh_token, decode_token

def test_create_and_decode_access_token_success():
    payload = {"sub": "user-123"}
    token = create_access_token(payload)
    
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-123"
    assert decoded["type"] == "access"
    assert "exp" in decoded

def test_create_and_decode_refresh_token_success():
    payload = {"sub": "user-456"}
    token = create_refresh_token(payload)
    
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-456"
    assert decoded["type"] == "refresh"
    assert "exp" in decoded

def test_decode_invalid_token():
    assert decode_token("invalid.token.signature") is None
    assert decode_token("") is None

def test_expired_token_returns_none():
    payload = {"sub": "expired-user"}
    # Generate token with negative lifespan so it is already expired
    token = create_access_token(payload, expires_delta=timedelta(seconds=-10))
    
    decoded = decode_token(token)
    assert decoded is None
