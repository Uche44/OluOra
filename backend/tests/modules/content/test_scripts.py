import json
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.modules.analysis.models import Analysis, Insight
from app.modules.content.models import (
    ContentCalendarItem,
    ContentOpportunity,
    ContentOpportunityEvidence,
    ContentScript,
)
from app.modules.users.models import SocialAccount, User
from app.modules.youtube.models import Channel, Video

pytestmark = pytest.mark.asyncio


def _headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def _script_payload() -> dict:
    return {
        "working_title": "The real cost of this camera",
        "hook": "Before you buy, here is the cost nobody mentions.",
        "body": "Walk through the body, lens, and accessory costs.",
        "sections": [
            {
                "heading": "The hidden costs",
                "content": (
                    "The body price is only the start.\n\n"
                    "The lens and accessories often add the most to the bill."
                ),
            },
            {
                "heading": "What to budget for",
                "content": "Plan for the body, one lens, and a spare battery.",
            },
        ],
        "talking_points": ["Body cost", "Lens cost", "Accessory cost"],
        "examples": ["Show the receipt breakdown"],
        "cta": "Subscribe for the full buying guide.",
        "caption": "The hidden costs of this camera.",
        "description": "A practical breakdown of what you actually pay.",
        "alt_titles": ["What this camera really costs", "Camera cost breakdown"],
    }


async def _seed(db: AsyncSession, email: str = "script@example.com") -> dict:
    user = User(email=email, full_name="Script Creator", is_active=True)
    db.add(user)
    await db.flush()

    channel = Channel(
        creator_id=user.id,
        platform="youtube",
        external_id=f"channel-{uuid.uuid4()}",
        title="Script Channel",
    )
    db.add(channel)
    await db.flush()

    video = Video(
        channel_id=channel.id,
        platform="youtube",
        external_id=f"video-{uuid.uuid4()}",
        title="Camera review",
        description="A practical test of the camera in low light and daylight.",
        url="https://www.youtube.com/watch?v=test-video",
        published_at=datetime.now(timezone.utc),
        sync_status="synced",
        transcript=(
            "In this video I compare the camera body and lens prices, "
            "then test low-light autofocus and battery life."
        ),
        transcript_fetched_at=datetime.now(timezone.utc),
    )
    db.add(video)
    await db.flush()

    analysis = Analysis(video_id=video.id, status="completed", comments_analyzed=5)
    db.add(analysis)
    await db.flush()

    db.add_all(
        [
            Insight(
                analysis_id=analysis.id,
                type="question",
                title="What does the camera actually cost?",
                content="Viewers want a clear body and lens price breakdown.",
            ),
            Insight(
                analysis_id=analysis.id,
                type="pain_point",
                title="Low-light autofocus is confusing",
                content="Viewers do not know which autofocus mode to use.",
            ),
        ]
    )
    await db.flush()

    opportunity = ContentOpportunity(
        creator_id=user.id,
        analysis_id=analysis.id,
        source_video_id=video.id,
        source_video_title=video.title,
        title="Camera pricing breakdown",
        rationale="Viewers repeatedly ask what the camera costs.",
        suggested_format="explainer",
        suggested_length="short",
        suggested_angle="Break down body and lens costs separately.",
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
            quote="What is the price of the camera?",
        )
    )

    item = ContentCalendarItem(
        creator_id=user.id,
        opportunity_id=opportunity.id,
        title=opportunity.title,
        angle=opportunity.suggested_angle,
        notes="Record at the desk.",
        content_context="The video is a hands-on camera review, not a pricing announcement.",
        format=opportunity.suggested_format,
        length=opportunity.suggested_length,
        platform="youtube",
        scheduled_date=date(2026, 11, 9),
        status="planned",
    )
    db.add(item)
    await db.commit()

    return {
        "user": user,
        "channel": channel,
        "video": video,
        "analysis": analysis,
        "opportunity": opportunity,
        "item": item,
    }


async def test_generate_script_uses_item_and_evidence(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db)

    with pytest.MonkeyPatch.context() as mp:
        mock = AsyncMock(return_value=json.dumps(_script_payload()))
        mp.setattr("app.modules.content.services.generate_chat_completion", mock)

        response = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["cached"] is False
    script = payload["data"]
    assert script["version"] == 1
    assert script["working_title"] == "The real cost of this camera"
    assert script["talking_points"] == ["Body cost", "Lens cost", "Accessory cost"]
    assert [section["heading"] for section in script["sections"]] == [
        "The hidden costs",
        "What to budget for",
    ]
    # Paragraph breaks survive generation and the flat body stays consistent.
    assert "\n\n" in script["sections"][0]["content"]
    assert "\n\n" in script["body"]
    assert "The hidden costs" in script["body"]
    assert script["model"]
    assert script["user_edited_at"] is None

    prompt = mock.call_args.kwargs["prompt"]
    assert "Camera pricing breakdown" in prompt
    assert "What is the price of the camera?" in prompt
    assert "Record at the desk." in prompt
    assert "A practical test of the camera" in prompt
    assert "In this video I compare" in prompt
    assert "hands-on camera review" in prompt
    assert "What does the camera actually cost?" in prompt
    assert "Low-light autofocus is confusing" in prompt
    assert "This is NOT a recap" in prompt
    assert "Return 3 to 6 script sections" in prompt
    system_prompt = mock.call_args.kwargs["system_prompt"]
    assert "Do not summarize, narrate, or recap" in system_prompt
    assert "paragraphs separated by blank lines" in system_prompt

    current = await client.get(
        f"/api/v1/content/calendar/items/{seed['item'].id}/script",
        headers=_headers(seed["user"]),
    )
    assert current.status_code == 200
    assert current.json()["id"] == script["id"]


async def test_update_script_sections_rebuilds_body(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="script-sections@example.com")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.modules.content.services.generate_chat_completion",
            AsyncMock(return_value=json.dumps(_script_payload())),
        )
        generated = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )

    script_id = generated.json()["data"]["id"]
    edited = await client.patch(
        f"/api/v1/content/scripts/{script_id}",
        headers=_headers(seed["user"]),
        json={
            "sections": [
                {
                    "heading": "Start here",
                    "content": "First paragraph.\n\nSecond paragraph.",
                },
                {"heading": "Next step", "content": "Do this next."},
            ]
        },
    )

    assert edited.status_code == 200, edited.text
    data = edited.json()
    assert [section["heading"] for section in data["sections"]] == [
        "Start here",
        "Next step",
    ]
    assert data["sections"][0]["content"] == (
        "First paragraph.\n\nSecond paragraph."
    )
    assert data["body"] == (
        "Start here\nFirst paragraph.\n\nSecond paragraph."
        "\n\nNext step\nDo this next."
    )

    fetched = await client.get(
        f"/api/v1/content/scripts/{script_id}",
        headers=_headers(seed["user"]),
    )
    assert fetched.status_code == 200
    assert fetched.json()["sections"] == data["sections"]


async def test_body_only_response_gets_section_fallback(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="script-body-fallback@example.com")
    payload = {
        "working_title": "A body-only script",
        "hook": "Start with the problem.",
        "body": (
            "THE PROBLEM\nMost creators buy gear before they know what they need."
            "\n\nWHAT TO DO\nStart with one camera and one lens."
        ),
    }

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.modules.content.services.generate_chat_completion",
            AsyncMock(return_value=json.dumps(payload)),
        )
        response = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )

    assert response.status_code == 200, response.text
    script = response.json()["data"]
    assert [section["heading"] for section in script["sections"]] == [
        "THE PROBLEM",
        "WHAT TO DO",
    ]
    assert script["body"].startswith("THE PROBLEM\nMost creators")


async def test_transcript_is_fetched_once_and_used_in_prompt(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="transcript-fetch@example.com")
    seed["video"].transcript = None
    seed["video"].transcript_fetched_at = None
    db.add(
        SocialAccount(
            user_id=seed["user"].id,
            provider="youtube",
            provider_user_id=f"google-{uuid.uuid4()}",
            access_token="fake-youtube-token",
            refresh_token="fake-refresh-token",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    await db.commit()

    with pytest.MonkeyPatch.context() as mp:
        fetch_mock = AsyncMock(
            return_value=("Fetched transcript about low-light testing.", 250)
        )
        mp.setattr(
            "app.modules.content.services.fetch_video_transcript", fetch_mock
        )
        llm_mock = AsyncMock(return_value=json.dumps(_script_payload()))
        mp.setattr(
            "app.modules.content.services.generate_chat_completion", llm_mock
        )

        first = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )
        second = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )

    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert fetch_mock.await_count == 1
    prompt = llm_mock.call_args.kwargs["prompt"]
    assert "Fetched transcript about low-light testing." in prompt
    assert seed["video"].transcript == "Fetched transcript about low-light testing."


async def test_script_caching_and_versioning_preserve_edits(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="script-versions@example.com")

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

    assert first.status_code == 200 and first.json()["cached"] is False
    assert cached.status_code == 200 and cached.json()["cached"] is True
    assert mock.await_count == 1

    version_one_id = first.json()["data"]["id"]
    edited = await client.patch(
        f"/api/v1/content/scripts/{version_one_id}",
        headers=_headers(seed["user"]),
        json={"hook": "My own edited hook.", "talking_points": ["One", "Two"]},
    )
    assert edited.status_code == 200
    assert edited.json()["hook"] == "My own edited hook."
    assert edited.json()["user_edited_at"] is not None

    with pytest.MonkeyPatch.context() as mp:
        mock_two = AsyncMock(return_value=json.dumps(_script_payload()))
        mp.setattr("app.modules.content.services.generate_chat_completion", mock_two)

        regenerated = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={"force": True},
        )

    assert regenerated.status_code == 200
    assert regenerated.json()["cached"] is False
    assert regenerated.json()["data"]["version"] == 2

    versions = await client.get(
        f"/api/v1/content/calendar/items/{seed['item'].id}/scripts",
        headers=_headers(seed["user"]),
    )
    assert versions.status_code == 200
    assert [item["version"] for item in versions.json()["data"]] == [2, 1]

    # The edited version 1 is still intact.
    old = await client.get(
        f"/api/v1/content/scripts/{version_one_id}",
        headers=_headers(seed["user"]),
    )
    assert old.status_code == 200
    assert old.json()["hook"] == "My own edited hook."

    persisted = (
        await db.execute(
            select(ContentScript).where(ContentScript.calendar_item_id == seed["item"].id)
        )
    ).scalars().all()
    assert len(persisted) == 2


async def test_script_endpoints_are_creator_scoped(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="script-owner@example.com")
    other = User(email="script-other@example.com", full_name="Other")
    db.add(other)
    await db.commit()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.modules.content.services.generate_chat_completion",
            AsyncMock(return_value=json.dumps(_script_payload())),
        )
        generated = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )
    script_id = generated.json()["data"]["id"]

    denied_generate = await client.post(
        f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
        headers=_headers(other),
        json={},
    )
    assert denied_generate.status_code == 404

    denied_get = await client.get(
        f"/api/v1/content/scripts/{script_id}",
        headers=_headers(other),
    )
    assert denied_get.status_code == 404

    denied_patch = await client.patch(
        f"/api/v1/content/scripts/{script_id}",
        headers=_headers(other),
        json={"hook": "Hijacked"},
    )
    assert denied_patch.status_code == 404

    denied_item = await client.get(
        f"/api/v1/content/calendar/items/{seed['item'].id}/script",
        headers=_headers(other),
    )
    assert denied_item.status_code == 404


async def test_malformed_script_response_returns_502(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="script-malformed@example.com")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.modules.content.services.generate_chat_completion",
            AsyncMock(return_value="not json"),
        )
        response = await client.post(
            f"/api/v1/content/calendar/items/{seed['item'].id}/script/generate",
            headers=_headers(seed["user"]),
            json={},
        )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "SCRIPT_GENERATION_FAILED"
