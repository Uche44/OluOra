import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.modules.analysis.models import (
    Analysis,
    CommentClusterMembership,
    Insight,
    TopicCluster,
)
from app.modules.comments.models import Comment
from app.modules.content.models import ContentOpportunity, ContentOpportunityEvidence
from app.modules.users.models import User
from app.modules.youtube.models import Channel, Video

pytestmark = pytest.mark.asyncio


async def _seed(db: AsyncSession, email: str = "content@example.com") -> dict:
    user = User(email=email, full_name="Content Creator", is_active=True)
    db.add(user)
    await db.flush()

    channel = Channel(
        creator_id=user.id,
        platform="youtube",
        external_id=f"channel-{uuid.uuid4()}",
        title="Content Channel",
    )
    db.add(channel)
    await db.flush()

    video = Video(
        channel_id=channel.id,
        platform="youtube",
        external_id=f"video-{uuid.uuid4()}",
        title="Camera buying guide",
        published_at=datetime.now(timezone.utc),
        sync_status="synced",
    )
    db.add(video)
    await db.flush()

    analysis = Analysis(video_id=video.id, status="completed", comments_analyzed=3)
    db.add(analysis)
    await db.flush()

    cluster = TopicCluster(
        analysis_id=analysis.id,
        title="Pricing Questions",
        summary="Viewers repeatedly ask what the camera costs.",
        size=3,
        sentiment_score=0.1,
    )
    db.add(cluster)
    await db.flush()

    insight = Insight(
        analysis_id=analysis.id,
        type="question",
        title="How much does it cost?",
        content="Several viewers ask about the camera price.",
    )
    db.add(insight)
    await db.flush()

    comments = []
    for i in range(3):
        comment = Comment(
            video_id=video.id,
            external_id=f"comment-{uuid.uuid4()}",
            author_name=f"Viewer {i}",
            text=f"Great video, but what is the price of the camera? ({i})",
            like_count=i,
            published_at=datetime.now(timezone.utc),
            embedding=[0.1] * 8,
            sentiment_score=0.0,
        )
        db.add(comment)
        comments.append(comment)
    await db.flush()

    for comment in comments:
        db.add(
            CommentClusterMembership(
                analysis_id=analysis.id,
                cluster_id=cluster.id,
                comment_id=comment.id,
                distance=0.1,
            )
        )

    await db.commit()
    return {
        "user": user,
        "channel": channel,
        "video": video,
        "analysis": analysis,
        "cluster": cluster,
        "insight": insight,
        "comments": comments,
    }


def _headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def _llm_payload(seed: dict, include_invalid: bool = True) -> dict:
    evidence = [
        {
            "insight_id": str(seed["insight"].id),
            "cluster_id": str(seed["cluster"].id),
            "comment_id": str(seed["comments"][0].id),
        }
    ]
    if include_invalid:
        evidence.append(
            {
                "insight_id": str(uuid.uuid4()),
                "comment_id": str(uuid.uuid4()),
            }
        )
    return {
        "opportunities": [
            {
                "title": "Camera pricing breakdown",
                "rationale": "Viewers repeatedly ask what the camera costs.",
                "suggested_format": "explainer",
                "suggested_length": "short",
                "suggested_angle": "Break down body and lens costs separately.",
                "priority": "high",
                "evidence": evidence,
            },
            {
                "title": "Unsupported idea",
                "rationale": "This one cites no real evidence.",
                "suggested_format": "tutorial",
                "suggested_length": "long_form",
                "suggested_angle": "Should be dropped.",
                "priority": "medium",
                "evidence": [{"insight_id": str(uuid.uuid4())}],
            },
        ]
    }


async def test_generate_opportunities_validates_evidence(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "app.modules.content.services.generate_chat_completion",
            AsyncMock(return_value=json.dumps(_llm_payload(seed))),
        )

        response = await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(seed["user"]),
            json={"analysis_id": str(seed["analysis"].id), "limit": 3},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["cached"] is False
    assert len(payload["data"]) == 1
    opportunity = payload["data"][0]
    assert opportunity["title"] == "Camera pricing breakdown"
    assert opportunity["suggested_length"] == "short"
    # Evidence is split by source: insight, cluster, and comment.
    assert len(opportunity["evidence"]) == 3
    insight_row = next(
        row for row in opportunity["evidence"] if row["insight_id"]
    )
    cluster_row = next(
        row for row in opportunity["evidence"] if row["cluster_id"]
    )
    comment_row = next(
        row for row in opportunity["evidence"] if row["comment_id"]
    )
    assert insight_row["quote"].startswith(seed["insight"].title)
    assert cluster_row["quote"] == seed["cluster"].summary
    assert comment_row["comment_id"] == str(seed["comments"][0].id)
    # The quote comes from the database, not from model output.
    assert comment_row["quote"] == seed["comments"][0].text

    persisted = (
        await db.execute(
            select(ContentOpportunity).where(
                ContentOpportunity.analysis_id == seed["analysis"].id
            )
        )
    ).scalars().all()
    assert len(persisted) == 1
    rows = (
        await db.execute(
            select(ContentOpportunityEvidence).where(
                ContentOpportunityEvidence.opportunity_id == persisted[0].id
            )
        )
    ).scalars().all()
    assert len(rows) == 3


async def test_generate_strips_identifiers_and_uses_short_refs(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="no-uuids@example.com")
    leaked_uuid = "bde78c23-46bc-44f1-96e6-f65bffd1b939"
    payload = {
        "opportunities": [
            {
                "title": f"Case study in Enugu ({leaked_uuid})",
                "rationale": (
                    f"High praise that the project is beautiful ({leaked_uuid}) "
                    "combined with a request (I1)."
                ),
                "suggested_format": "case_study",
                "suggested_length": "long_form",
                "suggested_angle": f"Show real impact [C1] ({leaked_uuid}).",
                "priority": "high",
                "evidence": [
                    {
                        "insight_ref": "I1",
                        "cluster_ref": "C1",
                        "comment_ref": "M1",
                    }
                ],
            }
        ]
    }

    with pytest.MonkeyPatch.context() as mp:
        mock = AsyncMock(return_value=json.dumps(payload))
        mp.setattr("app.modules.content.services.generate_chat_completion", mock)

        response = await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(seed["user"]),
            json={"analysis_id": str(seed["analysis"].id)},
        )

    assert response.status_code == 200, response.text
    opportunity = response.json()["data"][0]
    for field in ("title", "rationale", "suggested_angle"):
        assert leaked_uuid not in opportunity[field]
        assert "I1" not in opportunity[field]
        assert "C1" not in opportunity[field]

    assert any(
        row["insight_id"] == str(seed["insight"].id)
        for row in opportunity["evidence"]
    )
    assert any(
        row["cluster_id"] == str(seed["cluster"].id)
        for row in opportunity["evidence"]
    )
    assert any(
        row["comment_id"] == str(seed["comments"][0].id)
        for row in opportunity["evidence"]
    )

    prompt = mock.call_args.kwargs["prompt"]
    assert str(seed["insight"].id) not in prompt
    assert str(seed["cluster"].id) not in prompt
    assert "[I1]" in prompt
    assert "[C1]" in prompt
    assert "[M1]" in prompt


async def test_unrelated_evidence_is_dropped(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="evidence-filter@example.com")
    payload = {
        "opportunities": [
            {
                "title": "Camera pricing breakdown",
                "rationale": "Viewers repeatedly ask what the camera costs.",
                "suggested_format": "explainer",
                "suggested_length": "short",
                "suggested_angle": "Break down body and lens costs separately.",
                "priority": "high",
                "evidence": [
                    {"insight_ref": "I1", "comment_ref": "M1"},
                ],
            }
        ]
    }

    async def fake_embeddings(texts, allow_fallback=True):
        # The comment contains "great video"; the opportunity, insight, and
        # cluster evidence do not. The comment should be filtered out.
        return [
            [0.0, 1.0] if "great video" in text.lower() else [1.0, 0.0]
            for text in texts
        ]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(settings, "HF_API_KEY", "test-key")
        mp.setattr(
            "app.modules.content.services.generate_embeddings", fake_embeddings
        )
        mp.setattr(
            "app.modules.content.services.generate_chat_completion",
            AsyncMock(return_value=json.dumps(payload)),
        )

        response = await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(seed["user"]),
            json={"analysis_id": str(seed["analysis"].id)},
        )

    assert response.status_code == 200, response.text
    opportunity = response.json()["data"][0]
    assert opportunity["title"] == "Camera pricing breakdown"
    assert any(row["insight_id"] for row in opportunity["evidence"])
    assert not any(row["comment_id"] for row in opportunity["evidence"])


async def test_generate_opportunities_is_cached_until_forced(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="cache@example.com")

    with pytest.MonkeyPatch.context() as mp:
        from unittest.mock import AsyncMock

        mock = AsyncMock(return_value=json.dumps(_llm_payload(seed, include_invalid=False)))
        mp.setattr("app.modules.content.services.generate_chat_completion", mock)

        first = await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(seed["user"]),
            json={"analysis_id": str(seed["analysis"].id)},
        )
        second = await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(seed["user"]),
            json={"analysis_id": str(seed["analysis"].id)},
        )
        third = await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(seed["user"]),
            json={"analysis_id": str(seed["analysis"].id), "force": True},
        )

    assert first.status_code == 200 and first.json()["cached"] is False
    assert second.status_code == 200 and second.json()["cached"] is True
    assert third.status_code == 200 and third.json()["cached"] is False
    assert mock.await_count == 2


async def test_generate_opportunities_is_creator_scoped(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="owner@example.com")
    other = User(email="other@example.com", full_name="Other", is_active=True)
    db.add(other)
    await db.commit()

    with pytest.MonkeyPatch.context() as mp:
        from unittest.mock import AsyncMock

        mock = AsyncMock(return_value=json.dumps(_llm_payload(seed)))
        mp.setattr("app.modules.content.services.generate_chat_completion", mock)

        response = await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(other),
            json={"analysis_id": str(seed["analysis"].id)},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ANALYSIS_NOT_FOUND"
    # The model must never be called for another creator's analysis.
    assert mock.await_count == 0


async def test_generate_rejects_unsupported_opportunities(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="unsupported@example.com")
    payload = _llm_payload(seed)
    payload["opportunities"] = payload["opportunities"][1:]  # only invalid evidence

    with pytest.MonkeyPatch.context() as mp:
        from unittest.mock import AsyncMock

        mp.setattr(
            "app.modules.content.services.generate_chat_completion",
            AsyncMock(return_value=json.dumps(payload)),
        )

        response = await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(seed["user"]),
            json={"analysis_id": str(seed["analysis"].id)},
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INSUFFICIENT_EVIDENCE"


async def test_status_update_is_creator_scoped(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="status-owner@example.com")
    other = User(email="status-other@example.com", full_name="Other", is_active=True)
    db.add(other)
    await db.commit()

    with pytest.MonkeyPatch.context() as mp:
        from unittest.mock import AsyncMock

        mp.setattr(
            "app.modules.content.services.generate_chat_completion",
            AsyncMock(return_value=json.dumps(_llm_payload(seed, include_invalid=False))),
        )
        generated = await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(seed["user"]),
            json={"analysis_id": str(seed["analysis"].id)},
        )

    opportunity_id = generated.json()["data"][0]["id"]

    denied = await client.patch(
        f"/api/v1/content/opportunities/{opportunity_id}",
        headers=_headers(other),
        json={"status": "saved"},
    )
    assert denied.status_code == 404

    updated = await client.patch(
        f"/api/v1/content/opportunities/{opportunity_id}",
        headers=_headers(seed["user"]),
        json={"status": "saved"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "saved"


async def test_sources_only_include_completed_analyses(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="sources@example.com")

    # A running analysis for a second video must not appear as a source.
    other_video = Video(
        channel_id=seed["channel"].id,
        platform="youtube",
        external_id=f"video-{uuid.uuid4()}",
        title="Still analyzing",
        published_at=datetime.now(timezone.utc),
        sync_status="synced",
    )
    db.add(other_video)
    await db.flush()
    db.add(Analysis(video_id=other_video.id, status="running", comments_analyzed=0))
    await db.commit()

    response = await client.get(
        "/api/v1/content/opportunities/sources",
        headers=_headers(seed["user"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["analysis_id"] == str(seed["analysis"].id)
    assert data[0]["video_title"] == "Camera buying guide"


async def test_sources_collapse_reruns_to_latest_completed_analysis(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="sources-rerun@example.com")
    first_run = seed["analysis"]
    first_run.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    second_run = Analysis(
        video_id=seed["video"].id,
        status="completed",
        comments_analyzed=12,
        created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    db.add(second_run)
    await db.commit()

    response = await client.get(
        "/api/v1/content/opportunities/sources",
        headers=_headers(seed["user"]),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["analysis_id"] == str(second_run.id)
    assert data[0]["comments_analyzed"] == 12


async def test_list_opportunities_is_creator_scoped(
    client: AsyncClient, db: AsyncSession
):
    seed = await _seed(db, email="list-owner@example.com")
    other = User(email="list-other@example.com", full_name="Other", is_active=True)
    db.add(other)
    await db.commit()

    with pytest.MonkeyPatch.context() as mp:
        from unittest.mock import AsyncMock

        mp.setattr(
            "app.modules.content.services.generate_chat_completion",
            AsyncMock(return_value=json.dumps(_llm_payload(seed, include_invalid=False))),
        )
        await client.post(
            "/api/v1/content/opportunities/generate",
            headers=_headers(seed["user"]),
            json={"analysis_id": str(seed["analysis"].id)},
        )

    owner_response = await client.get(
        "/api/v1/content/opportunities",
        headers=_headers(seed["user"]),
    )
    assert owner_response.status_code == 200
    assert owner_response.json()["pagination"]["total"] == 1

    other_response = await client.get(
        "/api/v1/content/opportunities",
        headers=_headers(other),
    )
    assert other_response.status_code == 200
    assert other_response.json()["data"] == []
    assert other_response.json()["pagination"]["total"] == 0
