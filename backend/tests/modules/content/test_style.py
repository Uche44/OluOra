import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.analysis.models import Analysis
from app.modules.content.models import (
    ContentCalendarItem,
    ContentOpportunity,
    ContentOpportunityEvidence,
    ContentScript,
    CreatorStyleProfile,
)
from app.modules.users.models import User
from app.modules.youtube.models import Channel, Video

pytestmark = pytest.mark.asyncio


def _headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def _script_payload() -> dict:
    return {
        "working_title": "A beginner camera guide",
        "hook": "You do not need expensive gear to start.",
        "body": "Here is a simple path from phone footage to your first camera.",
        "talking_points": ["Start with what you have", "One lens is enough"],
        "examples": ["Show a phone-only setup"],
        "cta": "Subscribe for the next step.",
        "caption": "A beginner camera guide.",
        "description": "A practical guide for new creators.",
        "alt_titles": ["Start creating with less gear"],
    }


async def _seed(db: AsyncSession, email: str = "style@example.com") -> dict:
    user = User(email=email, full_name="Style Creator", is_active=True)
    db.add(user)
    await db.flush()

    channel = Channel(
        creator_id=user.id,
        platform="youtube",
        external_id=f"channel-{uuid.uuid4()}",
        title="Style Channel",
    )
    db.add(channel)
    await db.flush()

    video = Video(
        channel_id=channel.id,
        platform="youtube",
        external_id=f"video-{uuid.uuid4()}",
        title="Beginner camera video",
        published_at=datetime.now(timezone.utc),
        sync_status="synced",
    )
    db.add(video)
    await db.flush()

    analysis = Analysis(video_id=video.id, status="completed", comments_analyzed=3)
    db.add(analysis)
    await db.flush()

    opportunity = ContentOpportunity(
        creator_id=user.id,
        analysis_id=analysis.id,
        source_video_id=video.id,
        source_video_title=video.title,
        title="Beginner camera guide",
        rationale="Viewers ask where to start.",
        suggested_format="tutorial",
        suggested_length="long_form",
        suggested_angle="Start with the gear they already own.",
        priority="high",
        status="saved",
        is_evidence_backed=True,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(opportunity)
    await db.flush()

    db.add(
        ContentOpportunityEvidence(
            opportunity_id=opportunity.id,
            quote="I only have a phone. Can I still start?",
        )
    )

    item = ContentCalendarItem(
        creator_id=user.id,
        opportunity_id=opportunity.id,
        title=opportunity.title,
        angle=opportunity.suggested_angle,
        notes="",
        format=opportunity.suggested_format,
        length=opportunity.suggested_length,
        platform="youtube",
        scheduled_date=date(2026, 11, 9),
        status="planned",
    )
    db.add(item)
    await db.commit()
    return {"user": user, "item": item, "opportunity": opportunity}


async def test_get_style_defaults(client: AsyncClient, db: AsyncSession):
    seed = await _seed(db, email="style-defaults@example.com")
    response = await client.get(
        "/api/v1/content/style", headers=_headers(seed["user"])
    )
    assert response.status_code == 200
    data = response.json()
    assert data["technical_depth"] == "intermediate"
    assert data["preferred_structures"] == []
    assert data["avoid"] == []
    assert data["posting_cadence"] == 3
    assert data["updated_at"] is None


async def test_update_and_get_style(client: AsyncClient, db: AsyncSession):
    seed = await _seed(db, email="style-update@example.com")
    payload = {
        "tone": "Warm, direct, and practical",
        "language": "English",
        "audience_description": "Beginner photographers with a phone.",
        "technical_depth": "beginner",
        "preferred_structures": ["tutorial", "story"],
        "avoid": ["jargon", "long intros"],
        "posting_cadence": 4,
        "preferred_formats": ["tutorial", "faq"],
        "preferred_platforms": ["youtube"],
        "reference_notes": "Keep examples concrete.",
    }

    response = await client.put(
        "/api/v1/content/style",
        headers=_headers(seed["user"]),
        json=payload,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["tone"] == payload["tone"]
    assert data["technical_depth"] == "beginner"
    assert data["preferred_structures"] == ["tutorial", "story"]
    assert data["avoid"] == ["jargon", "long intros"]
    assert data["posting_cadence"] == 4
    assert data["updated_at"] is not None

    fetched = await client.get(
        "/api/v1/content/style", headers=_headers(seed["user"])
    )
    assert fetched.status_code == 200
    assert fetched.json()["tone"] == payload["tone"]

    row = (
        await db.execute(
            select(CreatorStyleProfile).where(
                CreatorStyleProfile.user_id == seed["user"].id
            )
        )
    ).scalars().first()
    assert row is not None
    assert row.preferred_formats == ["tutorial", "faq"]


async def test_style_is_creator_scoped(client: AsyncClient, db: AsyncSession):
    seed = await _seed(db, email="style-owner@example.com")
    other = User(email="style-other@example.com", full_name="Other")
    db.add(other)
    await db.commit()

    await client.put(
        "/api/v1/content/style",
        headers=_headers(seed["user"]),
        json={"tone": "Owner tone"},
    )

    other_response = await client.get(
        "/api/v1/content/style", headers=_headers(other)
    )
    assert other_response.status_code == 200
    assert other_response.json()["tone"] == ""


async def test_style_normalizes_invalid_values(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="style-normalize@example.com")
    response = await client.put(
        "/api/v1/content/style",
        headers=_headers(seed["user"]),
        json={
            "tone": "  Direct  ",
            "technical_depth": "expert",
            "preferred_structures": ["story", "invalid", "story"],
            "avoid": ["jargon", "Jargon", "  "],
            "preferred_formats": ["tutorial", "invalid"],
            "preferred_platforms": ["tiktok"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tone"] == "Direct"
    assert data["technical_depth"] == "intermediate"
    assert data["preferred_structures"] == ["story"]
    assert data["avoid"] == ["jargon"]
    assert data["preferred_formats"] == ["tutorial"]
    assert data["preferred_platforms"] == []


async def test_script_prompt_uses_style_and_style_change_versions(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="style-script@example.com")

    style = {
        "tone": "Warm and direct",
        "language": "English",
        "audience_description": "Complete beginners",
        "technical_depth": "beginner",
        "preferred_structures": ["tutorial"],
        "avoid": ["jargon"],
        "posting_cadence": 3,
        "preferred_formats": ["tutorial"],
        "preferred_platforms": ["youtube"],
        "reference_notes": "",
    }
    saved = await client.put(
        "/api/v1/content/style",
        headers=_headers(seed["user"]),
        json=style,
    )
    assert saved.status_code == 200

    with pytest.MonkeyPatch.context() as mp:
        mock = AsyncMock(return_value=json.dumps(_script_payload()))
        mp.setattr("app.modules.content.services.generate_chat_completion", mock)

        first = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )
        cached = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )

    assert first.status_code == 200, first.text
    assert first.json()["cached"] is False
    assert cached.status_code == 200 and cached.json()["cached"] is True
    assert mock.await_count == 1

    prompt = mock.call_args.kwargs["prompt"]
    assert "Warm and direct" in prompt
    assert "Complete beginners" in prompt
    assert "Technical depth: beginner" in prompt
    assert "Avoid: jargon" in prompt

    changed = await client.put(
        "/api/v1/content/style",
        headers=_headers(seed["user"]),
        json={**style, "tone": "Calm and analytical"},
    )
    assert changed.status_code == 200

    with pytest.MonkeyPatch.context() as mp:
        mock_two = AsyncMock(return_value=json.dumps(_script_payload()))
        mp.setattr("app.modules.content.services.generate_chat_completion", mock_two)
        regenerated = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )

    assert regenerated.status_code == 200
    assert regenerated.json()["cached"] is False
    assert regenerated.json()["data"]["version"] == 2
    assert "Calm and analytical" in mock_two.call_args.kwargs["prompt"]

    versions = (
        await db.execute(
            select(ContentScript)
            .where(ContentScript.calendar_item_id == seed["item"].id)
            .order_by(ContentScript.version.asc())
        )
    ).scalars().all()
    assert [version.version for version in versions] == [1, 2]
