from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.email.models import EmailMessage
from app.modules.email.services import EmailService
from app.modules.feedback.models import Feedback
from app.modules.users.models import User
from app.modules.waitlist.models import WaitlistEntry

pytestmark = pytest.mark.asyncio


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _make_user(
    db: AsyncSession,
    email: str,
    *,
    created_at: datetime | None = None,
    opted_out: bool = False,
) -> User:
    user = User(email=email, full_name="Ada Lovelace", is_active=True, is_admin=False)
    if created_at is not None:
        user.created_at = created_at
    if opted_out:
        user.email_opt_out_at = _now()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _add_waitlist(db: AsyncSession, email: str, *, unsubscribed: bool = False):
    entry = WaitlistEntry(email=email, source="test")
    if unsubscribed:
        entry.unsubscribed_at = _now()
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


# ---------------------------------------------------------------------------
# send()
# ---------------------------------------------------------------------------
async def test_send_logs_the_message(db: AsyncSession, recording_email_provider):
    message = await EmailService.send(
        db,
        category="signup_welcome",
        to="creator@oluora.com",
        subject="Welcome to OluOra",
        template="welcome_signup",
        context={"first_name": "Ada", "dashboard_url": "https://app/x/dashboard"},
    )

    assert message.status == "sent"
    assert message.provider == "recording"
    assert message.sent_at is not None
    assert message.provider_message_id == "test-1"
    assert recording_email_provider.sent[0].to == "creator@oluora.com"


async def test_marketing_send_adds_unsubscribe_link_and_headers(
    db: AsyncSession, recording_email_provider
):
    entry = await _add_waitlist(db, "fan@oluora.com")

    await EmailService.send(
        db,
        category="waitlist_welcome",
        to=entry.email,
        subject="You're on the OluOra waitlist",
        template="waitlist_welcome",
        opt_out_scope="waitlist",
        opt_out_id=entry.id,
    )

    sent = recording_email_provider.sent[-1]
    assert "/api/v1/email/unsubscribe?token=" in sent.html
    assert sent.headers["List-Unsubscribe"].startswith("<")
    assert sent.headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


async def test_transactional_send_has_no_unsubscribe(
    db: AsyncSession, recording_email_provider
):
    await EmailService.send(
        db,
        category="signup_welcome",
        to="creator@oluora.com",
        subject="Welcome",
        template="welcome_signup",
    )
    assert "Unsubscribe" not in recording_email_provider.sent[-1].html


# ---------------------------------------------------------------------------
# recipient selection
# ---------------------------------------------------------------------------
async def test_feedback_recipients_respects_min_age(db: AsyncSession):
    fresh = await _make_user(db, "fresh@oluora.com")
    old = await _make_user(db, "old@oluora.com", created_at=_now() - timedelta(days=5))

    recipients = await EmailService.feedback_recipients(
        db, min_age_days=1, cooldown_days=30, limit=100
    )
    ids = {u.id for u in recipients}
    assert old.id in ids
    assert fresh.id not in ids


async def test_feedback_recipients_excludes_feedback_and_opt_outs(db: AsyncSession):
    eligible = await _make_user(db, "eligible@oluora.com")
    has_feedback = await _make_user(db, "has_feedback@oluora.com")
    opted_out = await _make_user(db, "opted_out@oluora.com", opted_out=True)

    db.add(
        Feedback(
            user_id=has_feedback.id,
            email=has_feedback.email,
            category="idea",
            message="Add CSV export.",
        )
    )
    await db.commit()

    ids = {
        u.id
        for u in await EmailService.feedback_recipients(
            db, min_age_days=0, cooldown_days=30, limit=100
        )
    }
    assert eligible.id in ids
    assert has_feedback.id not in ids
    assert opted_out.id not in ids


async def test_feedback_recipients_respects_cooldown(db: AsyncSession):
    user = await _make_user(db, "reminded@oluora.com")
    db.add(
        EmailMessage(
            to_email=user.email,
            user_id=user.id,
            category="feedback_reminder",
            subject="How's OluOra going?",
            provider="recording",
            status="sent",
        )
    )
    await db.commit()

    ids = {
        u.id
        for u in await EmailService.feedback_recipients(
            db, min_age_days=0, cooldown_days=30, limit=100
        )
    }
    assert user.id not in ids


async def test_feedback_recipients_cooldown_expires(db: AsyncSession):
    user = await _make_user(db, "old_reminder@oluora.com")
    stale = EmailMessage(
        to_email=user.email,
        user_id=user.id,
        category="feedback_reminder",
        subject="How's OluOra going?",
        provider="recording",
        status="sent",
    )
    stale.created_at = _now() - timedelta(days=60)
    db.add(stale)
    await db.commit()

    ids = {
        u.id
        for u in await EmailService.feedback_recipients(
            db, min_age_days=0, cooldown_days=30, limit=100
        )
    }
    assert user.id in ids


async def test_waitlist_recipients_excludes_unsubscribed_and_registered(db: AsyncSession):
    await _add_waitlist(db, "open@oluora.com")
    await _add_waitlist(db, "unsub@oluora.com", unsubscribed=True)
    await _add_waitlist(db, "member@oluora.com")
    await _make_user(db, "member@oluora.com")

    default = {e.email for e in await EmailService.waitlist_recipients(db, limit=100)}
    assert "open@oluora.com" in default
    assert "unsub@oluora.com" not in default
    assert "member@oluora.com" not in default

    inclusive = {
        e.email
        for e in await EmailService.waitlist_recipients(
            db, limit=100, include_existing_users=True
        )
    }
    assert "member@oluora.com" in inclusive


async def test_waitlist_recipients_honours_limit(db: AsyncSession):
    for i in range(5):
        await _add_waitlist(db, f"limit{i}@oluora.com")
    assert len(await EmailService.waitlist_recipients(db, limit=2)) == 2


# ---------------------------------------------------------------------------
# unsubscribe()
# ---------------------------------------------------------------------------
async def test_unsubscribe_marks_both_scopes(db: AsyncSession):
    user = await _make_user(db, "optout@oluora.com")
    entry = await _add_waitlist(db, "wl@oluora.com")

    assert await EmailService.unsubscribe(
        db, scope="user", object_id=user.id, email="OPTOUT@oluora.com"
    )
    assert await EmailService.unsubscribe(
        db, scope="waitlist", object_id=entry.id, email="wl@oluora.com"
    )

    await db.refresh(user)
    await db.refresh(entry)
    assert user.email_opt_out_at is not None
    assert entry.unsubscribed_at is not None


async def test_unsubscribe_rejects_email_mismatch(db: AsyncSession):
    user = await _make_user(db, "real@oluora.com")
    assert not await EmailService.unsubscribe(
        db, scope="user", object_id=user.id, email="someone-else@oluora.com"
    )
    await db.refresh(user)
    assert user.email_opt_out_at is None


# ---------------------------------------------------------------------------
# batches + admin reads
# ---------------------------------------------------------------------------
async def test_finalize_batch_recomputes_counts(db: AsyncSession):
    batch = await EmailService.create_batch(
        db, category="waitlist_broadcast", subject="News", requested_by=None, total=0
    )
    db.add(
        EmailMessage(
            to_email="a@oluora.com",
            category="waitlist_broadcast",
            subject="News",
            provider="recording",
            status="sent",
            batch_id=batch.id,
        )
    )
    db.add(
        EmailMessage(
            to_email="b@oluora.com",
            category="waitlist_broadcast",
            subject="News",
            provider="recording",
            status="failed",
            error="boom",
            batch_id=batch.id,
        )
    )
    await db.commit()

    done = await EmailService.finalize_batch(db, batch)
    assert done.sent == 1
    assert done.failed == 1
    assert done.total == 2
    assert done.status == "completed"
    assert done.completed_at is not None


async def test_list_messages_filters_and_paginates(db: AsyncSession):
    db.add_all(
        [
            EmailMessage(
                to_email="one@oluora.com",
                category="signup_welcome",
                subject="Hi",
                provider="recording",
                status="sent",
            ),
            EmailMessage(
                to_email="two@oluora.com",
                category="feedback_reminder",
                subject="Hello",
                provider="recording",
                status="failed",
            ),
        ]
    )
    await db.commit()

    page = await EmailService.list_messages(db, page=1, limit=10)
    assert page["pagination"]["total"] >= 2

    filtered = await EmailService.list_messages(
        db, page=1, limit=10, category="feedback_reminder"
    )
    assert all(row.category == "feedback_reminder" for row in filtered["data"])

    searched = await EmailService.list_messages(db, page=1, limit=10, search="one@")
    assert any(row.to_email == "one@oluora.com" for row in searched["data"])
