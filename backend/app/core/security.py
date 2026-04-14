from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from app.core.config import settings

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    """
    Creates a JWT access token for a given user subject.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.ACCESS_TOKEN_EXPIRE_DAYS
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt
