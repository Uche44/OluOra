import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.users.models import User

pytestmark = pytest.mark.asyncio


async def _make_user(db: AsyncSession, email: str, is_admin: bool) -> User:
    user = User(
        email=email,
        full_name="Admin Tester",
        is_active=True,
        is_admin=is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


async def test_admin_endpoints_require_token(client: AsyncClient):
    response = await client.get("/api/v1/admin/overview")
    assert response.status_code in (401, 403)


async def test_admin_endpoint_forbidden_for_non_admin(client: AsyncClient, db: AsyncSession):
    user = await _make_user(db, "regular_user@oluora.com", is_admin=False)
    response = await client.get("/api/v1/admin/overview", headers=_auth(user))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


async def test_admin_endpoint_allows_admin(client: AsyncClient, db: AsyncSession):
    user = await _make_user(db, "admin_user@oluora.com", is_admin=True)
    response = await client.get("/api/v1/admin/overview", headers=_auth(user))
    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] >= 1
    assert "plan_split" in body
    assert "connected_accounts" in body


async def test_admin_me_returns_identity(client: AsyncClient, db: AsyncSession):
    user = await _make_user(db, "admin_me@oluora.com", is_admin=True)
    response = await client.get("/api/v1/admin/me", headers=_auth(user))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin_me@oluora.com"
    assert body["id"] == str(user.id)


async def test_admin_funnel_and_jobs_shapes(client: AsyncClient, db: AsyncSession):
    user = await _make_user(db, "admin_shapes@oluora.com", is_admin=True)
    headers = _auth(user)

    funnel = await client.get("/api/v1/admin/funnel", headers=headers)
    assert funnel.status_code == 200
    steps = funnel.json()["steps"]
    assert [step["key"] for step in steps][0] == "signed_up"
    counts = [step["count"] for step in steps]
    # Funnel counts must be non-increasing down the steps.
    assert counts == sorted(counts, reverse=True)

    jobs = await client.get("/api/v1/admin/jobs", headers=headers)
    assert jobs.status_code == 200
    assert "by_status" in jobs.json()


async def test_admin_users_and_waitlist_pagination(client: AsyncClient, db: AsyncSession):
    user = await _make_user(db, "admin_lists@oluora.com", is_admin=True)
    headers = _auth(user)

    users = await client.get("/api/v1/admin/users?page=1&limit=10", headers=headers)
    assert users.status_code == 200
    assert users.json()["pagination"]["page"] == 1

    waitlist = await client.get("/api/v1/admin/waitlist?page=1&limit=10", headers=headers)
    assert waitlist.status_code == 200
    assert waitlist.json()["pagination"]["limit"] == 10
