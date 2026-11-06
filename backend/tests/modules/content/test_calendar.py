import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.analysis.models import Analysis
from app.modules.content.models import ContentCalendarItem, ContentOpportunity
from app.modules.users.models import User
from app.modules.youtube.models import Channel, Video

pytestmark = pytest.mark.asyncio

MONDAY = date(2026, 11, 9)
WEDNESDAY = date(2026, 11, 11)
FRIDAY = date(2026, 11, 13)
SUNDAY = date(2026, 11, 15)
NEXT_MONDAY = date(2026, 11, 16)


async def _seed(db: AsyncSession, email: str) -> dict:
    user = User(email=email, full_name="Calendar Creator", is_active=True)
    db.add(user)
    await db.flush()

    channel = Channel(
        creator_id=user.id,
        platform="youtube",
        external_id=f"channel-{uuid.uuid4()}",
        title="Calendar Channel",
    )
    db.add(channel)
    await db.flush()

    video = Video(
        channel_id=channel.id,
        platform="youtube",
        external_id=f"video-{uuid.uuid4()}",
        title="Calendar source video",
        published_at=datetime.now(timezone.utc),
        sync_status="synced",
    )
    db.add(video)
    await db.flush()

    analysis = Analysis(video_id=video.id, status="completed", comments_analyzed=0)
    db.add(analysis)
    await db.commit()
    return {"user": user, "channel": channel, "video": video, "analysis": analysis}


def _headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


async def _add_opportunity(
    db: AsyncSession, seed: dict, title: str, status: str = "saved"
) -> ContentOpportunity:
    opportunity = ContentOpportunity(
        creator_id=seed["user"].id,
        analysis_id=seed["analysis"].id,
        source_video_id=seed["video"].id,
        source_video_title=seed["video"].title,
        title=title,
        rationale="Viewers asked for this.",
        suggested_format="explainer",
        suggested_length="short",
        suggested_angle="Keep it practical.",
        priority="high",
        status=status,
        is_evidence_backed=True,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(opportunity)
    await db.commit()
    return opportunity


async def test_create_calendar_item_from_opportunity_and_isolation(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="calendar-from-opp@example.com")
    opportunity = await _add_opportunity(db, seed, "Pricing breakdown")

    other = User(email="calendar-from-opp-other@example.com", full_name="Other")
    db.add(other)
    await db.commit()

    denied = await client.post(
        "/api/v1/content/calendar/items",
        headers=_headers(other),
        json={
            "opportunity_id": str(opportunity.id),
            "scheduled_date": MONDAY.isoformat(),
        },
    )
    assert denied.status_code == 404

    response = await client.post(
        "/api/v1/content/calendar/items",
        headers=_headers(seed["user"]),
        json={
            "opportunity_id": str(opportunity.id),
            "scheduled_date": MONDAY.isoformat(),
            "status": "planned",
            "scheduled_time": "09:30:00",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == "Pricing breakdown"
    assert data["format"] == "explainer"
    assert data["length"] == "short"
    assert data["angle"] == "Keep it practical."
    assert data["status"] == "planned"
    assert data["scheduled_date"] == MONDAY.isoformat()
    assert data["scheduled_time"] == "09:30:00"
    assert data["opportunity_id"] == str(opportunity.id)


async def test_opportunity_reflects_calendar_schedule(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="calendar-reflect@example.com")
    opportunity = await _add_opportunity(db, seed, "Scheduled opportunity")

    before = await client.get(
        "/api/v1/content/opportunities",
        headers=_headers(seed["user"]),
    )
    assert before.status_code == 200
    assert before.json()["data"][0]["is_scheduled"] is False
    assert before.json()["data"][0]["scheduled_dates"] == []

    created = await client.post(
        "/api/v1/content/calendar/items",
        headers=_headers(seed["user"]),
        json={
            "opportunity_id": str(opportunity.id),
            "scheduled_date": MONDAY.isoformat(),
            "status": "planned",
        },
    )
    assert created.status_code == 201

    after = await client.get(
        "/api/v1/content/opportunities",
        headers=_headers(seed["user"]),
    )
    assert after.status_code == 200
    scheduled = after.json()["data"][0]
    assert scheduled["is_scheduled"] is True
    assert scheduled["scheduled_dates"] == [MONDAY.isoformat()]

    detail = await client.get(
        f"/api/v1/content/opportunities/{opportunity.id}",
        headers=_headers(seed["user"]),
    )
    assert detail.status_code == 200
    assert detail.json()["is_scheduled"] is True


async def test_manual_item_requires_title(client: AsyncClient, db: AsyncSession):
    seed = await _seed(db, email="calendar-manual@example.com")

    invalid = await client.post(
        "/api/v1/content/calendar/items",
        headers=_headers(seed["user"]),
        json={"scheduled_date": MONDAY.isoformat()},
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "INVALID_CALENDAR_ITEM"

    response = await client.post(
        "/api/v1/content/calendar/items",
        headers=_headers(seed["user"]),
        json={
            "title": "Manual idea",
            "scheduled_date": WEDNESDAY.isoformat(),
            "format": "tutorial",
            "length": "long_form",
        },
    )
    assert response.status_code == 201
    assert response.json()["opportunity_id"] is None
    assert response.json()["status"] == "idea"


async def test_week_listing_uses_monday_and_sunday_bounds(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="calendar-week@example.com")
    db.add_all(
        [
            ContentCalendarItem(
                creator_id=seed["user"].id,
                title="Monday item",
                scheduled_date=MONDAY,
                status="planned",
            ),
            ContentCalendarItem(
                creator_id=seed["user"].id,
                title="Sunday item",
                scheduled_date=SUNDAY,
                status="idea",
            ),
            ContentCalendarItem(
                creator_id=seed["user"].id,
                title="Next week item",
                scheduled_date=NEXT_MONDAY,
                status="planned",
            ),
        ]
    )
    await db.commit()

    response = await client.get(
        f"/api/v1/content/calendar?week_start={WEDNESDAY.isoformat()}",
        headers=_headers(seed["user"]),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["week_start"] == MONDAY.isoformat()
    assert payload["week_end"] == SUNDAY.isoformat()
    assert [item["title"] for item in payload["data"]] == [
        "Monday item",
        "Sunday item",
    ]


async def test_update_move_and_delete_are_creator_scoped(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="calendar-update@example.com")
    item = ContentCalendarItem(
        creator_id=seed["user"].id,
        title="Original title",
        scheduled_date=MONDAY,
        status="idea",
    )
    db.add(item)
    other = User(email="calendar-update-other@example.com", full_name="Other")
    db.add(other)
    await db.commit()

    denied = await client.patch(
        f"/api/v1/content/calendar/items/{item.id}",
        headers=_headers(other),
        json={"status": "published"},
    )
    assert denied.status_code == 404

    updated = await client.patch(
        f"/api/v1/content/calendar/items/{item.id}",
        headers=_headers(seed["user"]),
        json={
            "title": "Moved title",
            "scheduled_date": FRIDAY.isoformat(),
            "scheduled_time": "14:00:00",
            "status": "in_progress",
            "notes": "Record on Thursday.",
        },
    )
    assert updated.status_code == 200
    data = updated.json()
    assert data["title"] == "Moved title"
    assert data["scheduled_date"] == FRIDAY.isoformat()
    assert data["scheduled_time"] == "14:00:00"
    assert data["status"] == "in_progress"
    assert data["notes"] == "Record on Thursday."

    fetched = await client.get(
        f"/api/v1/content/calendar/items/{item.id}",
        headers=_headers(seed["user"]),
    )
    assert fetched.status_code == 200

    denied_delete = await client.delete(
        f"/api/v1/content/calendar/items/{item.id}",
        headers=_headers(other),
    )
    assert denied_delete.status_code == 404

    deleted = await client.delete(
        f"/api/v1/content/calendar/items/{item.id}",
        headers=_headers(seed["user"]),
    )
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True

    missing = await client.get(
        f"/api/v1/content/calendar/items/{item.id}",
        headers=_headers(seed["user"]),
    )
    assert missing.status_code == 404


async def test_plan_week_is_deterministic_and_idempotent(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="calendar-plan@example.com")
    opportunities = [
        await _add_opportunity(db, seed, "Opportunity one"),
        await _add_opportunity(db, seed, "Opportunity two"),
        await _add_opportunity(db, seed, "Opportunity three"),
    ]

    payload = {
        "week_start": MONDAY.isoformat(),
        "opportunity_ids": [str(item.id) for item in opportunities],
        "days": [0, 2, 4],
    }
    first = await client.post(
        "/api/v1/content/calendar/plan",
        headers=_headers(seed["user"]),
        json=payload,
    )
    assert first.status_code == 200, first.text
    data = first.json()
    assert data["planned"] == 3
    assert [item["scheduled_date"] for item in data["data"]] == [
        MONDAY.isoformat(),
        WEDNESDAY.isoformat(),
        FRIDAY.isoformat(),
    ]
    assert all(item["status"] == "planned" for item in data["data"])
    assert [item["title"] for item in data["data"]] == [
        "Opportunity one",
        "Opportunity two",
        "Opportunity three",
    ]

    second = await client.post(
        "/api/v1/content/calendar/plan",
        headers=_headers(seed["user"]),
        json=payload,
    )
    assert second.status_code == 200
    assert second.json()["planned"] == 0


async def test_plan_week_rejects_foreign_opportunities(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="calendar-plan-owner@example.com")
    opportunity = await _add_opportunity(db, seed, "Owner opportunity")

    other = User(email="calendar-plan-other@example.com", full_name="Other")
    db.add(other)
    await db.commit()

    response = await client.post(
        "/api/v1/content/calendar/plan",
        headers=_headers(other),
        json={
            "week_start": MONDAY.isoformat(),
            "opportunity_ids": [str(opportunity.id)],
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "OPPORTUNITY_NOT_FOUND"
