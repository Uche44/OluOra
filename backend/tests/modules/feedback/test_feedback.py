import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.users.models import User

pytestmark = pytest.mark.asyncio


async def _make_user(db: AsyncSession, email: str, is_admin: bool = False) -> User:
    user = User(
        email=email,
        full_name="Feedback Tester",
        is_active=True,
        is_admin=is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


async def test_submit_feedback_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/feedback",
        json={"category": "idea", "message": "Great product"},
    )
    assert response.status_code in (401, 403)


async def test_submit_feedback_success(client: AsyncClient, db: AsyncSession):
    user = await _make_user(db, "feedback_author@oluora.com")

    response = await client.post(
        "/api/v1/feedback",
        headers=_auth(user),
        json={
            "rating": 5,
            "category": "praise",
            "message": "Love the new insights view.",
            "page": "/dashboard/insights",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["rating"] == 5
    assert body["category"] == "praise"
    assert body["message"] == "Love the new insights view."
    assert body["status"] == "new"


async def test_submit_feedback_validates_payload(client: AsyncClient, db: AsyncSession):
    user = await _make_user(db, "feedback_validation@oluora.com")
    headers = _auth(user)

    empty_message = await client.post(
        "/api/v1/feedback",
        headers=headers,
        json={"category": "bug", "message": ""},
    )
    assert empty_message.status_code == 422

    bad_rating = await client.post(
        "/api/v1/feedback",
        headers=headers,
        json={"rating": 9, "category": "bug", "message": "Too high"},
    )
    assert bad_rating.status_code == 422

    bad_category = await client.post(
        "/api/v1/feedback",
        headers=headers,
        json={"category": "not-a-category", "message": "Nope"},
    )
    assert bad_category.status_code == 422


async def test_admin_can_list_and_resolve_feedback(
    client: AsyncClient, db: AsyncSession
):
    author = await _make_user(db, "feedback_author2@oluora.com")
    admin = await _make_user(db, "feedback_admin@oluora.com", is_admin=True)

    created = await client.post(
        "/api/v1/feedback",
        headers=_auth(author),
        json={"rating": 3, "category": "idea", "message": "Add CSV export."},
    )
    assert created.status_code == 201
    feedback_id = created.json()["id"]

    listing = await client.get("/api/v1/admin/feedback?page=1&limit=10", headers=_auth(admin))
    assert listing.status_code == 200
    rows = listing.json()["data"]
    assert any(row["id"] == feedback_id for row in rows)

    resolved = await client.patch(
        f"/api/v1/admin/feedback/{feedback_id}",
        headers=_auth(admin),
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    filtered = await client.get(
        "/api/v1/admin/feedback?status=resolved", headers=_auth(admin)
    )
    assert filtered.status_code == 200
    assert all(row["status"] == "resolved" for row in filtered.json()["data"])


async def test_admin_feedback_requires_admin(client: AsyncClient, db: AsyncSession):
    user = await _make_user(db, "feedback_nonadmin@oluora.com", is_admin=False)
    response = await client.get("/api/v1/admin/feedback", headers=_auth(user))
    assert response.status_code == 403


async def test_admin_update_unknown_feedback_404(client: AsyncClient, db: AsyncSession):
    admin = await _make_user(db, "feedback_admin2@oluora.com", is_admin=True)
    response = await client.patch(
        f"/api/v1/admin/feedback/{uuid.uuid4()}",
        headers=_auth(admin),
        json={"status": "resolved"},
    )
    assert response.status_code == 404
