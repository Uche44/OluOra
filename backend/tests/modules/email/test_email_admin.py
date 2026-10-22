import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.modules.email import admin_router as email_admin_router
from app.modules.email import internal_router as email_internal_router
from app.modules.email.tokens import create_unsubscribe_token
from app.modules.users.models import User
from app.modules.waitlist.models import WaitlistEntry

pytestmark = pytest.mark.asyncio


async def _make_user(db: AsyncSession, email: str, *, is_admin: bool = False) -> User:
    user = User(email=email, full_name="Email Tester", is_active=True, is_admin=is_admin)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.fixture
def queued_tasks(monkeypatch):
    """Capture background-task scheduling without running the send loops."""
    calls: list = []

    def spy(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(email_admin_router, "send_feedback_reminders_task", spy)
    monkeypatch.setattr(email_admin_router, "send_waitlist_broadcast_task", spy)
    monkeypatch.setattr(email_internal_router, "send_feedback_reminders_task", spy)
    return calls


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_admin_email_requires_admin(client: AsyncClient, db: AsyncSession):
    member = await _make_user(db, "email_member@oluora.com", is_admin=False)
    response = await client.get("/api/v1/admin/email/messages", headers=_auth(member))
    assert response.status_code == 403

    anonymous = await client.get("/api/v1/admin/email/messages")
    assert anonymous.status_code in (401, 403)


async def test_admin_can_list_messages(client: AsyncClient, db: AsyncSession):
    admin = await _make_user(db, "email_admin@oluora.com", is_admin=True)
    response = await client.get(
        "/api/v1/admin/email/messages?page=1&limit=10", headers=_auth(admin)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["page"] == 1
    assert isinstance(body["data"], list)


async def test_admin_can_list_batches(client: AsyncClient, db: AsyncSession):
    admin = await _make_user(db, "email_admin2@oluora.com", is_admin=True)
    response = await client.get("/api/v1/admin/email/batches", headers=_auth(admin))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Feedback reminders
# ---------------------------------------------------------------------------
async def test_feedback_reminders_dry_run_queues_nothing(
    client: AsyncClient, db: AsyncSession, queued_tasks
):
    admin = await _make_user(db, "email_admin3@oluora.com", is_admin=True)
    await _make_user(db, "needs_reminder@oluora.com")

    response = await client.post(
        "/api/v1/admin/email/feedback-reminders",
        headers=_auth(admin),
        json={"min_age_days": 0, "dry_run": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["recipients"] >= 1
    assert body["queued"] == 0
    assert body["batch_id"] is None
    assert queued_tasks == []


async def test_feedback_reminders_queues_a_batch(
    client: AsyncClient, db: AsyncSession, queued_tasks
):
    admin = await _make_user(db, "email_admin4@oluora.com", is_admin=True)
    await _make_user(db, "remind_me@oluora.com")

    response = await client.post(
        "/api/v1/admin/email/feedback-reminders",
        headers=_auth(admin),
        json={"min_age_days": 0, "limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is False
    assert body["queued"] == body["recipients"] >= 1
    assert body["batch_id"] is not None
    assert len(queued_tasks) == 1


# ---------------------------------------------------------------------------
# Waitlist broadcast
# ---------------------------------------------------------------------------
async def test_waitlist_broadcast_dry_run_and_send(
    client: AsyncClient, db: AsyncSession, queued_tasks
):
    admin = await _make_user(db, "email_admin5@oluora.com", is_admin=True)
    db.add(WaitlistEntry(email="listener@oluora.com", source="test"))
    await db.commit()

    dry = await client.post(
        "/api/v1/admin/email/waitlist-broadcast",
        headers=_auth(admin),
        json={"subject": "We're live", "body": "First para.\n\nSecond para.", "dry_run": True},
    )
    assert dry.status_code == 200
    assert dry.json()["recipients"] >= 1
    assert dry.json()["batch_id"] is None

    sent = await client.post(
        "/api/v1/admin/email/waitlist-broadcast",
        headers=_auth(admin),
        json={"subject": "We're live", "body": "First para.\n\nSecond para."},
    )
    assert sent.status_code == 200
    assert sent.json()["queued"] == sent.json()["recipients"] >= 1
    assert len(queued_tasks) == 1


async def test_waitlist_broadcast_validates_payload(
    client: AsyncClient, db: AsyncSession, queued_tasks
):
    admin = await _make_user(db, "email_admin6@oluora.com", is_admin=True)
    headers = _auth(admin)

    missing_subject = await client.post(
        "/api/v1/admin/email/waitlist-broadcast",
        headers=headers,
        json={"subject": "", "body": "Body"},
    )
    assert missing_subject.status_code == 422

    missing_body = await client.post(
        "/api/v1/admin/email/waitlist-broadcast",
        headers=headers,
        json={"subject": "Subject", "body": ""},
    )
    assert missing_body.status_code == 422


# ---------------------------------------------------------------------------
# Internal cron endpoint
# ---------------------------------------------------------------------------
async def test_internal_endpoint_disabled_without_secret(
    client: AsyncClient, monkeypatch, queued_tasks
):
    monkeypatch.setattr(settings, "INTERNAL_CRON_SECRET", "")
    response = await client.post("/api/v1/internal/email/run")
    assert response.status_code == 503


async def test_internal_endpoint_rejects_wrong_secret(
    client: AsyncClient, monkeypatch, queued_tasks
):
    monkeypatch.setattr(settings, "INTERNAL_CRON_SECRET", "s3cret")
    response = await client.post(
        "/api/v1/internal/email/run", headers={"X-Internal-Secret": "nope"}
    )
    assert response.status_code == 401


async def test_internal_endpoint_runs_with_correct_secret(
    client: AsyncClient, db: AsyncSession, monkeypatch, queued_tasks
):
    monkeypatch.setattr(settings, "INTERNAL_CRON_SECRET", "s3cret")
    monkeypatch.setattr(settings, "FEEDBACK_REMINDER_MIN_AGE_DAYS", 0)
    await _make_user(db, "cron_reminder@oluora.com")

    response = await client.post(
        "/api/v1/internal/email/run", headers={"X-Internal-Secret": "s3cret"}
    )
    assert response.status_code == 200
    assert response.json()["queued"] >= 1
    assert len(queued_tasks) == 1


# ---------------------------------------------------------------------------
# Public unsubscribe endpoint
# ---------------------------------------------------------------------------
async def test_unsubscribe_endpoint_invalid_token(client: AsyncClient):
    response = await client.get("/api/v1/email/unsubscribe?token=garbage")
    assert response.status_code == 400


async def test_unsubscribe_endpoint_opts_user_out(client: AsyncClient, db: AsyncSession):
    user = await _make_user(db, "unsub_me@oluora.com")
    token = create_unsubscribe_token(scope="user", object_id=user.id, email=user.email)

    response = await client.get(f"/api/v1/email/unsubscribe?token={token}")
    assert response.status_code == 200
    assert "unsubscribed" in response.text.lower()

    await db.refresh(user)
    assert user.email_opt_out_at is not None


async def test_unsubscribe_endpoint_rejects_unknown_record(
    client: AsyncClient, db: AsyncSession
):
    token = create_unsubscribe_token(
        scope="user", object_id=uuid.uuid4(), email="ghost@oluora.com"
    )
    response = await client.get(f"/api/v1/email/unsubscribe?token={token}")
    assert response.status_code == 400
