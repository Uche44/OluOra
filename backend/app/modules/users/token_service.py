import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.modules.users.models import RefreshToken, User


def hash_token(token: str) -> str:
    """Return a SHA-256 hex digest of a token string."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_refresh_token(
    db: AsyncSession,
    user_id,
    token: str,
    jti: str,
    expires_delta: timedelta | None = None,
) -> RefreshToken:
    """Persist an issued refresh token (only stores its hash)."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    row = RefreshToken(
        user_id=user_id,
        jti=jti,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + expires_delta,
        revoked=False,
    )
    db.add(row)
    await db.commit()
    return row


async def validate_refresh_token(db: AsyncSession, token: str):
    """
    Validate a refresh token against the server-side registry.

    Returns ``(refresh_token_row, user)`` on success, else ``None``.

    Checks:
      * JWT is a valid, unexpired ``refresh`` token with a ``jti`` claim.
      * A DB record exists for that ``jti``.
      * The provided token's hash matches the stored hash (rejects tampering).
      * The token is not already revoked/consumed (rejects reuse after rotation).
      * The token is not expired and belongs to an active user.
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    jti = payload.get("jti")
    if not jti:
        return None

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    row = result.scalar_one_or_none()
    if not row:
        return None
    if row.token_hash != hash_token(token):
        return None
    if row.revoked:
        return None
    if datetime.now(timezone.utc) > row.expires_at:
        return None

    user_result = await db.execute(select(User).where(User.id == row.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    return row, user


async def revoke_refresh_token(db: AsyncSession, row: RefreshToken) -> None:
    """Mark a single refresh token as revoked (used on rotation)."""
    row.revoked = True
    row.revoked_at = datetime.now(timezone.utc)
    await db.commit()


async def revoke_all_user_refresh_tokens(db: AsyncSession, user_id) -> None:
    """Revoke every non-revoked refresh token for a user (used on logout)."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
    )
    rows = result.scalars().all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.revoked = True
        row.revoked_at = now
    if rows:
        await db.commit()


async def revoke_by_token(db: AsyncSession, token: str) -> User | None:
    """
    Revoke the refresh token matching ``token`` (and all of its owner's others).
    Returns the user if one was found, else None. Used by the logout endpoint.
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    jti = payload.get("jti")
    if not jti:
        return None

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    row = result.scalar_one_or_none()
    if not row:
        return None

    await revoke_all_user_refresh_tokens(db, row.user_id)
    user_result = await db.execute(select(User).where(User.id == row.user_id))
    return user_result.scalar_one_or_none()