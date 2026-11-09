"""Content opportunity generation and persistence.

Everything here is scoped to the authenticated creator. The LLM is given stable
IDs for insights, clusters, and representative comments; any ID it returns is
validated against that creator's analysis before it is saved.
"""

import hashlib
import json
import logging
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import numpy as np
from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.integrations.groq import generate_chat_completion
from app.integrations.huggingface import generate_embeddings
from app.integrations.youtube import fetch_video_transcript
from app.modules.analysis.models import (
    Analysis,
    CommentClusterMembership,
    Insight,
    TopicCluster,
)
from app.modules.comments.models import Comment
from app.modules.content.models import (
    ContentCalendarItem,
    ContentOpportunity,
    ContentOpportunityEvidence,
    ContentScript,
    CreatorStyleProfile,
)
from app.modules.content.schemas import (
    CalendarItemCreate,
    CalendarItemUpdate,
    LLMOpportunitiesResponse,
    LLMOpportunity,
    ScriptContent,
    ScriptSection,
    ScriptUpdate,
    StyleProfileUpdate,
)
from app.modules.users.models import User
from app.modules.users.quota import log_api_quota, verify_quota_limit
from app.modules.users.social_tokens import get_or_refresh_social_token, get_social_account
from app.modules.youtube.models import Channel, Video

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = ("tutorial", "explainer", "comparison", "faq", "demo", "opinion")
ALLOWED_LENGTHS = ("long_form", "short")
ALLOWED_PRIORITIES = ("high", "medium", "low")
ALLOWED_CALENDAR_STATUSES = ("idea", "planned", "in_progress", "ready", "published")
ALLOWED_DEPTHS = ("beginner", "intermediate", "advanced")
ALLOWED_STRUCTURES = (
    "hook_first",
    "story",
    "tutorial",
    "listicle",
    "case_study",
    "problem_solution",
    "comparison",
)
ALLOWED_PLATFORMS = ("youtube",)
COMMENTS_PER_CLUSTER = 3
MAX_INSIGHTS_IN_PROMPT = 40

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_ALIAS_CITATION_RE = re.compile(
    r"[\(\[]\s*(?:[ICM]\d+\s*[,;]?\s*)+\s*[\)\]]"
)
_EMPTY_BRACKETS_RE = re.compile(r"[\(\[]\s*[\)\]]")
_ID_LABEL_RE = re.compile(
    r"\b(?:insight|cluster|comment)_(?:id|ref)\s*[:=]\s*", re.IGNORECASE
)


def _strip_identifiers(value: str) -> str:
    """Remove UUIDs, citation aliases, and dangling punctuation from model text.

    The model is given short references for evidence, but it sometimes copies
    IDs into prose. Generated text fields must never contain them.
    """
    if not value:
        return ""
    cleaned = _UUID_RE.sub("", value)
    cleaned = _ALIAS_CITATION_RE.sub("", cleaned)
    cleaned = _ID_LABEL_RE.sub("", cleaned)
    cleaned = _EMPTY_BRACKETS_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned.strip()


def _strip_identifiers_preserving_paragraphs(value: str) -> str:
    """Remove model artifacts while keeping headings and paragraph breaks."""
    if not value:
        return ""
    cleaned = _UUID_RE.sub("", value)
    cleaned = _ALIAS_CITATION_RE.sub("", cleaned)
    cleaned = _ID_LABEL_RE.sub("", cleaned)
    cleaned = _EMPTY_BRACKETS_RE.sub("", cleaned)

    lines: list[str] = []
    previous_blank = False
    for raw_line in cleaned.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            lines.append(line)
            previous_blank = False
        elif lines and not previous_blank:
            lines.append("")
            previous_blank = True
    return "\n".join(lines).strip()


def _style_defaults() -> dict:
    return {
        "tone": "",
        "language": "",
        "audience_description": "",
        "technical_depth": "intermediate",
        "preferred_structures": [],
        "avoid": [],
        "posting_cadence": 3,
        "preferred_formats": [],
        "preferred_platforms": ["youtube"],
        "reference_notes": "",
        "updated_at": None,
    }


class OpportunityError(Exception):
    """Base class for expected content-strategy failures."""


class AnalysisNotFoundError(OpportunityError):
    """The analysis does not exist or is not owned by the current creator."""


class AnalysisNotReadyError(OpportunityError):
    """The analysis has not completed successfully yet."""


class OpportunityGenerationError(OpportunityError):
    """The model call failed or returned unusable output."""


class InsufficientEvidenceError(OpportunityError):
    """No proposed opportunity could be tied to valid audience evidence."""


class OpportunityNotFoundError(OpportunityError):
    """The opportunity does not exist or is not owned by the current creator."""


class CalendarItemNotFoundError(OpportunityError):
    """The calendar item does not exist or is not owned by the current creator."""


class InvalidCalendarRequestError(OpportunityError):
    """The calendar request is missing required fields or has invalid values."""


class ScriptNotFoundError(OpportunityError):
    """No script exists for this item, or the script is not owned by the creator."""


class ScriptGenerationError(OpportunityError):
    """The script model call failed or returned unusable output."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _load_context(
    db: AsyncSession, user: User, analysis_id: uuid.UUID
) -> dict:
    analysis = (
        await db.execute(
            select(Analysis)
            .join(Video, Video.id == Analysis.video_id)
            .join(Channel, Channel.id == Video.channel_id)
            .where(Analysis.id == analysis_id, Channel.creator_id == user.id)
        )
    ).scalars().first()
    if not analysis:
        raise AnalysisNotFoundError("Analysis not found.")

    video = (
        await db.execute(select(Video).where(Video.id == analysis.video_id))
    ).scalars().first()

    insights = (
        await db.execute(
            select(Insight)
            .where(Insight.analysis_id == analysis_id)
            .order_by(Insight.type.asc(), Insight.created_at.asc())
        )
    ).scalars().all()

    clusters = (
        await db.execute(
            select(TopicCluster)
            .where(TopicCluster.analysis_id == analysis_id)
            .order_by(TopicCluster.size.desc())
        )
    ).scalars().all()

    membership_rows = await db.execute(
        select(CommentClusterMembership.cluster_id, Comment)
        .join(Comment, Comment.id == CommentClusterMembership.comment_id)
        .where(CommentClusterMembership.analysis_id == analysis_id)
        .order_by(CommentClusterMembership.distance.asc())
    )
    comments_by_cluster: dict[uuid.UUID, list[Comment]] = {}
    for cluster_id, comment in membership_rows:
        bucket = comments_by_cluster.setdefault(cluster_id, [])
        if len(bucket) < COMMENTS_PER_CLUSTER:
            bucket.append(comment)

    return {
        "analysis": analysis,
        "video": video,
        "insights": list(insights),
        "clusters": list(clusters),
        "comments_by_cluster": comments_by_cluster,
    }


def _generation_hash(analysis: Analysis, limit: int) -> str:
    stamp = analysis.updated_at or analysis.created_at or _utcnow()
    raw = f"opportunity-v2:{analysis.id}:{stamp.isoformat()}:{limit}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_reference_map(context: dict) -> dict:
    """Map real UUIDs to short prompt aliases and back.

    The model never sees a UUID, so it cannot copy one into the prose.
    """
    insights: list[Insight] = context["insights"][:MAX_INSIGHTS_IN_PROMPT]
    clusters: list[TopicCluster] = context["clusters"]
    comments_by_cluster: dict[uuid.UUID, list[Comment]] = context["comments_by_cluster"]

    insight_by_ref = {f"I{index + 1}": item.id for index, item in enumerate(insights)}
    cluster_by_ref = {f"C{index + 1}": item.id for index, item in enumerate(clusters)}
    insight_ref_by_id = {
        str(item.id): f"I{index + 1}" for index, item in enumerate(insights)
    }
    cluster_ref_by_id = {
        str(item.id): f"C{index + 1}" for index, item in enumerate(clusters)
    }

    comment_by_ref: dict[str, uuid.UUID] = {}
    comment_ref_by_id: dict[str, str] = {}
    counter = 1
    for cluster in clusters:
        for comment in comments_by_cluster.get(cluster.id, []):
            ref = f"M{counter}"
            counter += 1
            comment_by_ref[ref] = comment.id
            comment_ref_by_id[str(comment.id)] = ref

    return {
        "insight_by_ref": insight_by_ref,
        "cluster_by_ref": cluster_by_ref,
        "comment_by_ref": comment_by_ref,
        "insight_ref_by_id": insight_ref_by_id,
        "cluster_ref_by_id": cluster_ref_by_id,
        "comment_ref_by_id": comment_ref_by_id,
    }


def _build_prompt(context: dict, limit: int, refs: dict) -> tuple[str, str]:
    insights: list[Insight] = context["insights"]
    clusters: list[TopicCluster] = context["clusters"]
    comments_by_cluster: dict[uuid.UUID, list[Comment]] = context["comments_by_cluster"]
    video: Video | None = context["video"]

    insight_lines = [
        f"[{refs['insight_ref_by_id'][str(i.id)]}] ({i.type}) {i.title}: {i.content}"
        for i in insights[:MAX_INSIGHTS_IN_PROMPT]
    ]

    cluster_lines: list[str] = []
    comment_lines: list[str] = []
    for cluster in clusters:
        cluster_ref = refs["cluster_ref_by_id"][str(cluster.id)]
        cluster_lines.append(
            f"[{cluster_ref}] {cluster.title} | "
            f"{cluster.size} comments | sentiment {cluster.sentiment_score:.2f} | "
            f"{cluster.summary}"
        )
        for comment in comments_by_cluster.get(cluster.id, []):
            comment_ref = refs["comment_ref_by_id"][str(comment.id)]
            text = " ".join((comment.text or "").split())[:280]
            comment_lines.append(f"[{comment_ref}] cluster {cluster_ref}: {text}")

    system_prompt = (
        "You are a content strategist working for a video creator. "
        "Turn the supplied audience evidence into specific, useful content opportunities.\n"
        "Hard rules:\n"
        "- Use ONLY the evidence supplied. Never invent comments, statistics, or audience claims.\n"
        "- Every opportunity must cite at least one evidence reference from the lists.\n"
        "- Cite only evidence that directly supports the specific opportunity. "
        "Do not cite a comment merely because it belongs to the same cluster.\n"
        "- Prefer insight or cluster evidence for the overall idea. Use a comment only "
        "when its text clearly supports the title/rationale.\n"
        "- Keep evidence entries separate: use one source per entry, not several unrelated sources combined.\n"
        "- In the evidence array, use ONLY the short references shown (I1, C1, M1). "
        "Do not use UUIDs or create new references.\n"
        "- Never include references, UUIDs, or bracket labels in title, rationale, or suggested_angle.\n"
        "- If the evidence is thin, propose fewer opportunities rather than inventing support.\n"
        f"- suggested_format must be one of: {', '.join(ALLOWED_FORMATS)}.\n"
        f"- suggested_length must be one of: {', '.join(ALLOWED_LENGTHS)}.\n"
        f"- priority must be one of: {', '.join(ALLOWED_PRIORITIES)}.\n"
        "- Return only valid JSON, with no Markdown wrapper or commentary.\n"
        "JSON shape:\n"
        "{\n"
        '  "opportunities": [\n'
        "    {\n"
        '      "title": "Short content topic",\n'
        '      "rationale": "Why this matters to this audience, grounded in the evidence.",\n'
        '      "suggested_format": "tutorial",\n'
        '      "suggested_length": "long_form",\n'
        '      "suggested_angle": "A useful way to approach it.",\n'
        '      "priority": "high",\n'
        '      "evidence": [\n'
        '        {"insight_ref": "I1", "cluster_ref": "C1", "comment_ref": "M1"}\n'
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}"
    )

    user_prompt = (
        f'Video: "{video.title if video else "Unknown video"}"\n'
        f'Video description: {(video.description if video else "") or "(none)"}\n\n'
        "AUDIENCE INSIGHTS:\n"
        + ("\n".join(insight_lines) if insight_lines else "(none)")
        + "\n\nTOPIC CLUSTERS:\n"
        + ("\n".join(cluster_lines) if cluster_lines else "(none)")
        + "\n\nREPRESENTATIVE COMMENTS:\n"
        + ("\n".join(comment_lines) if comment_lines else "(none)")
        + f"\n\nPropose up to {limit} opportunities. "
        "Each must include at least one valid evidence reference. "
        "Write clean prose: never put an I1/C1/M1 reference or a UUID in the "
        "title, rationale, or angle. Prefer specificity over volume."
    )
    return user_prompt, system_prompt


def _parse_llm_response(raw: str) -> list[LLMOpportunity]:
    clean = (raw or "").strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    try:
        payload = json.loads(clean)
        parsed = LLMOpportunitiesResponse.model_validate(payload)
    except Exception as exc:
        logger.warning("Content opportunity LLM response was not valid JSON: %s", exc)
        raise OpportunityGenerationError(
            "The AI returned an unusable response. Please try again."
        ) from exc
    return parsed.opportunities


def _choice(value: str | None, allowed: tuple[str, ...], default: str) -> str:
    normalized = (value or "").strip().lower()
    return normalized if normalized in allowed else default


def _as_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _resolve_reference(value, by_ref: dict, allowed_ids: set) -> uuid.UUID | None:
    if not value:
        return None
    raw = str(value).strip()
    if raw in by_ref:
        return by_ref[raw]
    parsed = _as_uuid(raw)
    if parsed and parsed in allowed_ids:
        return parsed
    return None


def _validate_opportunities(
    proposed: list[LLMOpportunity], context: dict, limit: int, refs: dict
) -> list[dict]:
    """Validate IDs against this analysis and build persistence-ready dicts."""
    insights_by_id = {item.id: item for item in context["insights"]}
    clusters_by_id = {item.id: item for item in context["clusters"]}
    comments_by_id = {
        comment.id: comment
        for bucket in context["comments_by_cluster"].values()
        for comment in bucket
    }
    insight_ids = set(insights_by_id)
    cluster_ids = set(clusters_by_id)
    comment_ids = set(comments_by_id)

    normalized: list[dict] = []
    seen_titles: set[str] = set()

    for item in proposed:
        title = _strip_identifiers(item.title or "").strip()
        rationale = _strip_identifiers(item.rationale or "").strip()
        if not title or not rationale:
            continue

        title_key = title.lower()
        if title_key in seen_titles:
            continue

        evidence: list[dict] = []
        seen_evidence: set[tuple] = set()

        for raw in item.evidence:
            insight_id = _resolve_reference(
                raw.insight_ref or raw.insight_id,
                refs["insight_by_ref"],
                insight_ids,
            )
            cluster_id = _resolve_reference(
                raw.cluster_ref or raw.cluster_id,
                refs["cluster_by_ref"],
                cluster_ids,
            )
            comment_id = _resolve_reference(
                raw.comment_ref or raw.comment_id,
                refs["comment_by_ref"],
                comment_ids,
            )

            insight = insights_by_id.get(insight_id) if insight_id else None
            cluster = clusters_by_id.get(cluster_id) if cluster_id else None
            comment = comments_by_id.get(comment_id) if comment_id else None

            # Drop IDs that do not belong to this analysis.
            if insight is None:
                insight_id = None
            if cluster is None:
                cluster_id = None
            if comment is None:
                comment_id = None

            candidates: list[dict] = []
            if insight is not None:
                candidates.append(
                    {
                        "insight_id": insight_id,
                        "cluster_id": None,
                        "comment_id": None,
                        "quote": f"{insight.title}: {insight.content}"[:500],
                    }
                )
            if cluster is not None:
                candidates.append(
                    {
                        "insight_id": None,
                        "cluster_id": cluster_id,
                        "comment_id": None,
                        "quote": (cluster.summary or cluster.title)[:500],
                    }
                )
            if comment is not None:
                candidates.append(
                    {
                        "insight_id": None,
                        "cluster_id": None,
                        "comment_id": comment_id,
                        "quote": " ".join((comment.text or "").split())[:500],
                    }
                )

            for row in candidates:
                key = (
                    row["insight_id"],
                    row["cluster_id"],
                    row["comment_id"],
                )
                if key in seen_evidence:
                    continue
                seen_evidence.add(key)
                evidence.append(row)

        # An unsupported idea must not be presented as audience-derived.
        if not evidence:
            logger.info("Dropping opportunity without valid evidence: %s", title)
            continue

        seen_titles.add(title_key)
        normalized.append(
            {
                "title": title[:255],
                "rationale": rationale,
                "suggested_format": _choice(item.suggested_format, ALLOWED_FORMATS, "tutorial"),
                "suggested_length": _choice(item.suggested_length, ALLOWED_LENGTHS, "long_form"),
                "suggested_angle": _strip_identifiers(item.suggested_angle or "").strip(),
                "priority": _choice(item.priority, ALLOWED_PRIORITIES, "medium"),
                "evidence": evidence,
            }
        )
        if len(normalized) >= limit:
            break

    return normalized


def _cosine_similarity(a, b) -> float:
    a_array = np.asarray(a, dtype=np.float32)
    b_array = np.asarray(b, dtype=np.float32)
    denominator = float(np.linalg.norm(a_array) * np.linalg.norm(b_array))
    if denominator == 0:
        return 0.0
    return float(np.dot(a_array, b_array) / denominator)


async def _filter_unrelated_evidence(
    opportunities: list[dict],
) -> list[dict]:
    """Drop cited evidence that is not semantically close to the opportunity.

    The model can cite an insight, theme, or comment that is from the right
    analysis but unrelated to the specific idea. This second check compares the
    opportunity text with each evidence quote using the analysis embedding model.
    """
    if not opportunities or not settings.HF_API_KEY:
        return opportunities

    evidence_rows: list[tuple[int, int, str]] = []
    for opportunity_index, opportunity in enumerate(opportunities):
        for evidence_index, evidence in enumerate(opportunity["evidence"]):
            if evidence.get("quote"):
                evidence_rows.append(
                    (opportunity_index, evidence_index, evidence["quote"])
                )

    if not evidence_rows:
        return opportunities

    opportunity_texts = [
        " ".join(
            filter(
                None,
                [
                    opportunity["title"],
                    opportunity["rationale"],
                    opportunity.get("suggested_angle", ""),
                ],
            )
        )
        for opportunity in opportunities
    ]
    unique_evidence_texts = list(dict.fromkeys(row[2] for row in evidence_rows))
    texts = opportunity_texts + unique_evidence_texts

    try:
        vectors = await generate_embeddings(texts, allow_fallback=False)
    except Exception as exc:
        logger.warning("Skipping evidence relevance check: %s", exc)
        return opportunities

    if len(vectors) != len(texts):
        logger.warning("Skipping evidence relevance check: embedding count mismatch")
        return opportunities

    opportunity_vectors = vectors[: len(opportunity_texts)]
    evidence_vectors = dict(
        zip(unique_evidence_texts, vectors[len(opportunity_texts) :])
    )

    remove: dict[int, set[int]] = {}
    for opportunity_index, evidence_index, quote in evidence_rows:
        try:
            similarity = _cosine_similarity(
                opportunity_vectors[opportunity_index], evidence_vectors[quote]
            )
        except Exception:
            continue
        if similarity < settings.OPPORTUNITY_EVIDENCE_MIN_SIMILARITY:
            remove.setdefault(opportunity_index, set()).add(evidence_index)
            logger.info(
                "Dropping unrelated evidence for '%s' (similarity=%.2f)",
                opportunities[opportunity_index]["title"],
                similarity,
            )

    if not remove:
        return opportunities

    filtered: list[dict] = []
    for opportunity_index, opportunity in enumerate(opportunities):
        if opportunity_index in remove:
            opportunity["evidence"] = [
                evidence
                for index, evidence in enumerate(opportunity["evidence"])
                if index not in remove[opportunity_index]
            ]
        if opportunity["evidence"]:
            filtered.append(opportunity)
    return filtered


async def _calendar_dates_for_opportunities(
    db: AsyncSession, user: User, opportunity_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[date]]:
    if not opportunity_ids:
        return {}
    rows = await db.execute(
        select(
            ContentCalendarItem.opportunity_id,
            ContentCalendarItem.scheduled_date,
        ).where(
            ContentCalendarItem.creator_id == user.id,
            ContentCalendarItem.opportunity_id.in_(opportunity_ids),
        )
    )
    dates: dict[uuid.UUID, set[date]] = {}
    for opportunity_id, scheduled_date in rows:
        if opportunity_id:
            dates.setdefault(opportunity_id, set()).add(scheduled_date)
    return {key: sorted(value) for key, value in dates.items()}


def _serialize_opportunity(
    opportunity: ContentOpportunity, scheduled_dates: list[date] | None = None
) -> dict:
    dates = sorted(set(scheduled_dates or []))
    return {
        "id": opportunity.id,
        "analysis_id": opportunity.analysis_id,
        "source_video_id": opportunity.source_video_id,
        "source_video_title": opportunity.source_video_title,
        "title": _strip_identifiers(opportunity.title),
        "rationale": _strip_identifiers(opportunity.rationale),
        "suggested_format": opportunity.suggested_format,
        "suggested_length": opportunity.suggested_length,
        "suggested_angle": _strip_identifiers(opportunity.suggested_angle),
        "priority": opportunity.priority,
        "status": opportunity.status,
        "is_evidence_backed": opportunity.is_evidence_backed,
        "is_scheduled": bool(dates),
        "scheduled_dates": dates,
        "generated_at": opportunity.generated_at,
        "evidence": [
            {
                "id": evidence.id,
                "insight_id": evidence.insight_id,
                "cluster_id": evidence.cluster_id,
                "comment_id": evidence.comment_id,
                "quote": evidence.quote,
            }
            for evidence in opportunity.evidence
        ],
    }


async def generate_opportunities(
    db: AsyncSession,
    user: User,
    analysis_id: uuid.UUID,
    limit: int = 3,
    force: bool = False,
) -> tuple[list[dict], bool]:
    """Generate (or reuse) opportunities for one completed analysis."""
    context = await _load_context(db, user, analysis_id)
    analysis: Analysis = context["analysis"]
    if analysis.status != "completed":
        raise AnalysisNotReadyError("This analysis has not completed yet.")

    generation_hash = _generation_hash(analysis, limit)

    if not force:
        existing = (
            await db.execute(
                select(ContentOpportunity)
                .options(selectinload(ContentOpportunity.evidence))
                .where(
                    ContentOpportunity.creator_id == user.id,
                    ContentOpportunity.generation_hash == generation_hash,
                )
                .order_by(ContentOpportunity.created_at.asc())
            )
        ).scalars().all()
        if existing:
            scheduled = await _calendar_dates_for_opportunities(
                db, user, [item.id for item in existing]
            )
            return [
                _serialize_opportunity(item, scheduled.get(item.id))
                for item in existing
            ], True

    refs = _build_reference_map(context)
    user_prompt, system_prompt = _build_prompt(context, limit, refs)

    try:
        raw = await generate_chat_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            json_mode=True,
        )
    except Exception as exc:
        logger.exception("Opportunity generation model call failed")
        raise OpportunityGenerationError(
            "Content generation is unavailable right now. Please try again."
        ) from exc

    proposed = _parse_llm_response(raw)
    normalized = _validate_opportunities(proposed, context, limit, refs)
    normalized = await _filter_unrelated_evidence(normalized)
    if not normalized:
        raise InsufficientEvidenceError(
            "We could not ground any suggestions in the available audience insights. "
            "Try a different analysis or add more comments."
        )

    if force:
        # Replace the previous generated set only after a usable new set exists.
        # Anything the creator saved — or already scheduled — is preserved.
        await db.execute(
            delete(ContentOpportunity).where(
                ContentOpportunity.creator_id == user.id,
                ContentOpportunity.generation_hash == generation_hash,
                ContentOpportunity.status != "saved",
                ~exists(
                    select(ContentCalendarItem.id).where(
                        ContentCalendarItem.opportunity_id == ContentOpportunity.id
                    )
                ),
            )
        )

    video: Video | None = context["video"]
    generated_at = _utcnow()
    created: list[ContentOpportunity] = []

    for item in normalized:
        opportunity = ContentOpportunity(
            creator_id=user.id,
            analysis_id=analysis.id,
            source_video_id=video.id if video else None,
            source_video_title=video.title if video else None,
            title=item["title"],
            rationale=item["rationale"],
            suggested_format=item["suggested_format"],
            suggested_length=item["suggested_length"],
            suggested_angle=item["suggested_angle"],
            priority=item["priority"],
            status="new",
            is_evidence_backed=True,
            generation_hash=generation_hash,
            generated_at=generated_at,
        )
        db.add(opportunity)
        await db.flush()

        for evidence in item["evidence"]:
            db.add(
                ContentOpportunityEvidence(
                    opportunity_id=opportunity.id,
                    insight_id=evidence["insight_id"],
                    cluster_id=evidence["cluster_id"],
                    comment_id=evidence["comment_id"],
                    quote=evidence["quote"],
                )
            )
        created.append(opportunity)

    await db.commit()

    persisted = (
        await db.execute(
            select(ContentOpportunity)
            .options(selectinload(ContentOpportunity.evidence))
            .where(ContentOpportunity.id.in_([item.id for item in created]))
            .order_by(ContentOpportunity.created_at.asc())
        )
    ).scalars().all()

    logger.info(
        "Generated %d evidence-backed opportunities for analysis_id=%s",
        len(persisted),
        analysis_id,
    )
    return [_serialize_opportunity(item) for item in persisted], False

async def list_opportunities(
    db: AsyncSession,
    user: User,
    status: str | None = None,
    analysis_id: uuid.UUID | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    filters = [ContentOpportunity.creator_id == user.id]
    if status:
        filters.append(ContentOpportunity.status == status)
    if analysis_id:
        filters.append(ContentOpportunity.analysis_id == analysis_id)

    total = (
        await db.execute(
            select(func.count())
            .select_from(ContentOpportunity)
            .where(*filters)
        )
    ).scalar_one()

    offset = (page - 1) * limit
    rows = (
        await db.execute(
            select(ContentOpportunity)
            .options(selectinload(ContentOpportunity.evidence))
            .where(*filters)
            .order_by(
                ContentOpportunity.generated_at.desc(),
                ContentOpportunity.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    scheduled = await _calendar_dates_for_opportunities(
        db, user, [item.id for item in rows]
    )
    return [
        _serialize_opportunity(item, scheduled.get(item.id)) for item in rows
    ], int(total)


async def get_opportunity(
    db: AsyncSession, user: User, opportunity_id: uuid.UUID
) -> dict:
    opportunity = (
        await db.execute(
            select(ContentOpportunity)
            .options(selectinload(ContentOpportunity.evidence))
            .where(
                ContentOpportunity.id == opportunity_id,
                ContentOpportunity.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not opportunity:
        raise OpportunityNotFoundError("Opportunity not found.")
    scheduled = await _calendar_dates_for_opportunities(
        db, user, [opportunity.id]
    )
    return _serialize_opportunity(opportunity, scheduled.get(opportunity.id))


async def update_opportunity_status(
    db: AsyncSession, user: User, opportunity_id: uuid.UUID, status: str
) -> dict:
    opportunity = (
        await db.execute(
            select(ContentOpportunity)
            .options(selectinload(ContentOpportunity.evidence))
            .where(
                ContentOpportunity.id == opportunity_id,
                ContentOpportunity.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not opportunity:
        raise OpportunityNotFoundError("Opportunity not found.")

    opportunity.status = status
    db.add(opportunity)
    await db.commit()
    scheduled = await _calendar_dates_for_opportunities(
        db, user, [opportunity.id]
    )
    return _serialize_opportunity(opportunity, scheduled.get(opportunity.id))


async def list_analysis_sources(db: AsyncSession, user: User) -> list[dict]:
    """List the creator's analyzed videos, one entry per video.

    Each analysis is an immutable run, so re-analyzing a video adds another
    completed row for the same ``video_id``. The opportunity picker is a video
    picker, so rank runs per video and keep only the newest completed one.
    """
    ranked = (
        select(
            Analysis.id.label("analysis_id"),
            func.row_number()
            .over(
                partition_by=Analysis.video_id,
                order_by=(Analysis.created_at.desc(), Analysis.id.desc()),
            )
            .label("run_rank"),
        )
        .where(Analysis.status == "completed")
        .subquery()
    )
    rows = await db.execute(
        select(Analysis, Video)
        .join(ranked, ranked.c.analysis_id == Analysis.id)
        .join(Video, Video.id == Analysis.video_id)
        .join(Channel, Channel.id == Video.channel_id)
        .where(
            Channel.creator_id == user.id,
            ranked.c.run_rank == 1,
        )
        .order_by(Analysis.created_at.desc())
    )
    return [
        {
            "analysis_id": analysis.id,
            "video_id": video.id,
            "video_title": video.title,
            "thumbnail_url": video.thumbnail_url,
            "platform": video.platform,
            "comments_analyzed": analysis.comments_analyzed,
            "created_at": analysis.created_at,
        }
        for analysis, video in rows
    ]


# --- Weekly calendar --------------------------------------------------------


def _monday(value: date | None) -> date:
    target = value or date.today()
    return target - timedelta(days=target.weekday())


def _serialize_calendar_item(item: ContentCalendarItem) -> dict:
    return {
        "id": item.id,
        "opportunity_id": item.opportunity_id,
        "title": item.title,
        "angle": item.angle,
        "notes": item.notes,
        "content_context": item.content_context,
        "format": item.format,
        "length": item.length,
        "platform": item.platform,
        "scheduled_date": item.scheduled_date,
        "scheduled_time": item.scheduled_time,
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


async def list_week_items(
    db: AsyncSession, user: User, week_start: date | None = None
) -> tuple[date, date, list[dict]]:
    monday = _monday(week_start)
    sunday = monday + timedelta(days=6)
    rows = (
        await db.execute(
            select(ContentCalendarItem)
            .where(
                ContentCalendarItem.creator_id == user.id,
                ContentCalendarItem.scheduled_date >= monday,
                ContentCalendarItem.scheduled_date <= sunday,
            )
            .order_by(
                ContentCalendarItem.scheduled_date.asc(),
                ContentCalendarItem.scheduled_time.asc().nulls_last(),
                ContentCalendarItem.created_at.asc(),
            )
        )
    ).scalars().all()
    return monday, sunday, [_serialize_calendar_item(item) for item in rows]


async def create_calendar_item(
    db: AsyncSession, user: User, payload: CalendarItemCreate
) -> dict:
    opportunity = None
    if payload.opportunity_id:
        opportunity = (
            await db.execute(
                select(ContentOpportunity).where(
                    ContentOpportunity.id == payload.opportunity_id,
                    ContentOpportunity.creator_id == user.id,
                )
            )
        ).scalars().first()
        if not opportunity:
            raise OpportunityNotFoundError("Opportunity not found.")

    title = (payload.title or (opportunity.title if opportunity else "")).strip()
    if not title:
        raise InvalidCalendarRequestError("A title is required.")

    item = ContentCalendarItem(
        creator_id=user.id,
        opportunity_id=opportunity.id if opportunity else None,
        title=title[:255],
        angle=(
            payload.angle
            if payload.angle is not None
            else (opportunity.suggested_angle if opportunity else "")
        ),
        notes=payload.notes or "",
        content_context=payload.content_context or "",
        format=_choice(
            payload.format or (opportunity.suggested_format if opportunity else None),
            ALLOWED_FORMATS,
            "tutorial",
        ),
        length=_choice(
            payload.length or (opportunity.suggested_length if opportunity else None),
            ALLOWED_LENGTHS,
            "long_form",
        ),
        platform=(payload.platform or "youtube")[:50],
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time,
        status=_choice(payload.status, ALLOWED_CALENDAR_STATUSES, "idea"),
    )
    db.add(item)
    await db.commit()
    return _serialize_calendar_item(item)


async def get_calendar_item(
    db: AsyncSession, user: User, item_id: uuid.UUID
) -> dict:
    item = (
        await db.execute(
            select(ContentCalendarItem).where(
                ContentCalendarItem.id == item_id,
                ContentCalendarItem.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not item:
        raise CalendarItemNotFoundError("Calendar item not found.")
    return _serialize_calendar_item(item)


async def update_calendar_item(
    db: AsyncSession, user: User, item_id: uuid.UUID, payload: CalendarItemUpdate
) -> dict:
    item = (
        await db.execute(
            select(ContentCalendarItem).where(
                ContentCalendarItem.id == item_id,
                ContentCalendarItem.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not item:
        raise CalendarItemNotFoundError("Calendar item not found.")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "title":
            title = (value or "").strip()
            if not title:
                raise InvalidCalendarRequestError("A title is required.")
            item.title = title[:255]
        elif key == "format":
            item.format = _choice(value, ALLOWED_FORMATS, item.format)
        elif key == "length":
            item.length = _choice(value, ALLOWED_LENGTHS, item.length)
        elif key == "status":
            item.status = _choice(value, ALLOWED_CALENDAR_STATUSES, item.status)
        elif key == "platform":
            item.platform = (value or item.platform)[:50]
        elif key == "angle":
            item.angle = value or ""
        elif key == "notes":
            item.notes = value or ""
        elif key == "content_context":
            item.content_context = value or ""
        elif key == "scheduled_date":
            if value is not None:
                item.scheduled_date = value
        elif key == "scheduled_time":
            item.scheduled_time = value

    db.add(item)
    await db.commit()
    return _serialize_calendar_item(item)


async def delete_calendar_item(db: AsyncSession, user: User, item_id: uuid.UUID) -> None:
    item = (
        await db.execute(
            select(ContentCalendarItem).where(
                ContentCalendarItem.id == item_id,
                ContentCalendarItem.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not item:
        raise CalendarItemNotFoundError("Calendar item not found.")
    await db.delete(item)
    await db.commit()


async def plan_week(
    db: AsyncSession,
    user: User,
    week_start: date,
    opportunity_ids: list[uuid.UUID],
    days: list[int],
    platform: str = "youtube",
) -> list[dict]:
    """Deterministically place selected opportunities into a week.

    Defaults to Monday/Wednesday/Friday. Existing items for the same
    opportunities in that week are skipped, so pressing Plan twice does not
    create duplicates.
    """
    monday = _monday(week_start)
    sunday = monday + timedelta(days=6)

    # Preserve caller order while removing duplicates.
    ordered_ids = list(dict.fromkeys(opportunity_ids))
    opportunities = (
        await db.execute(
            select(ContentOpportunity).where(
                ContentOpportunity.id.in_(ordered_ids),
                ContentOpportunity.creator_id == user.id,
            )
        )
    ).scalars().all()
    by_id = {item.id: item for item in opportunities}
    if len(by_id) != len(ordered_ids):
        raise OpportunityNotFoundError("One or more opportunities were not found.")

    valid_days = sorted({day for day in days if 0 <= day <= 6}) or [0, 2, 4]

    existing = (
        await db.execute(
            select(ContentCalendarItem).where(
                ContentCalendarItem.creator_id == user.id,
                ContentCalendarItem.scheduled_date >= monday,
                ContentCalendarItem.scheduled_date <= sunday,
                ContentCalendarItem.opportunity_id.in_(ordered_ids),
            )
        )
    ).scalars().all()
    existing_opportunity_ids = {
        item.opportunity_id for item in existing if item.opportunity_id
    }

    created: list[ContentCalendarItem] = []
    slot = 0
    for opportunity_id in ordered_ids:
        if opportunity_id in existing_opportunity_ids:
            continue
        opportunity = by_id[opportunity_id]
        scheduled_date = monday + timedelta(days=valid_days[slot % len(valid_days)])
        item = ContentCalendarItem(
            creator_id=user.id,
            opportunity_id=opportunity.id,
            title=opportunity.title,
            angle=opportunity.suggested_angle,
            notes="",
            format=opportunity.suggested_format,
            length=opportunity.suggested_length,
            platform=platform or "youtube",
            scheduled_date=scheduled_date,
            scheduled_time=None,
            status="planned",
        )
        db.add(item)
        created.append(item)
        slot += 1

    await db.commit()

    if not created:
        return []

    created_ids = [item.id for item in created]
    persisted = (
        await db.execute(
            select(ContentCalendarItem)
            .where(ContentCalendarItem.id.in_(created_ids))
            .order_by(
                ContentCalendarItem.scheduled_date.asc(),
                ContentCalendarItem.created_at.asc(),
            )
        )
    ).scalars().all()
    return [_serialize_calendar_item(item) for item in persisted]


# --- Scripts / content briefs ----------------------------------------------

MAX_SCRIPT_SECTIONS = 20
MAX_SECTION_HEADING_LENGTH = 120


def _section_value(section, field: str) -> str:
    if isinstance(section, dict):
        return section.get(field) or ""
    return getattr(section, field, "") or ""


def _clean_sections(
    sections, *, clean_identifiers: bool = True
) -> list[dict]:
    cleaned: list[dict] = []
    for section in sections or []:
        raw_heading = str(_section_value(section, "heading")).strip()
        raw_content = str(_section_value(section, "content")).strip()
        if clean_identifiers:
            heading = _strip_identifiers(raw_heading)
            content = _strip_identifiers_preserving_paragraphs(raw_content)
        else:
            heading = raw_heading
            content = raw_content
        heading = heading.strip()[:MAX_SECTION_HEADING_LENGTH]
        content = content.strip()
        if not heading and not content:
            continue
        cleaned.append({"heading": heading, "content": content})
        if len(cleaned) >= MAX_SCRIPT_SECTIONS:
            break
    return cleaned


def _body_from_sections(sections: list[dict]) -> str:
    blocks: list[str] = []
    for section in sections:
        heading = (section.get("heading") or "").strip()
        content = (section.get("content") or "").strip()
        if heading and content:
            blocks.append(f"{heading}\n{content}")
        elif heading or content:
            blocks.append(heading or content)
    return "\n\n".join(blocks)


def _looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 90:
        return False
    if stripped.endswith(":"):
        return True
    letters = [character for character in stripped if character.isalpha()]
    return (
        bool(letters)
        and all(character.isupper() for character in letters)
        and len(stripped.split()) <= 8
    )


def _sections_from_body(body: str) -> list[dict]:
    """Give older body-only scripts an editable section breakdown."""
    text = _strip_identifiers_preserving_paragraphs(body or "")
    if not text:
        return []

    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    sections: list[dict] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        heading = ""
        content = block
        if len(lines) > 1 and _looks_like_heading(lines[0]):
            heading = _strip_identifiers(lines[0].rstrip(":").strip())[
                :MAX_SECTION_HEADING_LENGTH
            ]
            content = "\n".join(lines[1:]).strip()
        if heading or content:
            sections.append({"heading": heading, "content": content})
        if len(sections) >= MAX_SCRIPT_SECTIONS:
            break
    return sections


def _serialize_script(script: ContentScript) -> dict:
    sections = script.sections or _sections_from_body(script.body)
    return {
        "id": script.id,
        "calendar_item_id": script.calendar_item_id,
        "version": script.version,
        "working_title": script.working_title,
        "hook": script.hook,
        "body": script.body,
        "sections": sections,
        "talking_points": script.talking_points or [],
        "examples": script.examples or [],
        "cta": script.cta,
        "caption": script.caption,
        "description": script.description,
        "alt_titles": script.alt_titles or [],
        "model": script.model,
        "generated_at": script.generated_at,
        "user_edited_at": script.user_edited_at,
        "created_at": script.created_at,
        "updated_at": script.updated_at,
    }


# --- Creator style profile ---------------------------------------------------


def _serialize_style(profile: CreatorStyleProfile | None) -> dict:
    if not profile:
        return _style_defaults()
    return {
        "tone": profile.tone,
        "language": profile.language,
        "audience_description": profile.audience_description,
        "technical_depth": profile.technical_depth,
        "preferred_structures": profile.preferred_structures or [],
        "avoid": profile.avoid or [],
        "posting_cadence": profile.posting_cadence,
        "preferred_formats": profile.preferred_formats or [],
        "preferred_platforms": profile.preferred_platforms or [],
        "reference_notes": profile.reference_notes,
        "updated_at": profile.updated_at,
    }


def _clean_allowed_list(values: list[str], allowed: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values or []:
        normalized = str(value).strip().lower()
        if normalized and normalized in allowed and normalized not in seen:
            seen.add(normalized)
            cleaned.append(normalized)
    return cleaned


def _clean_free_list(values: list[str], limit: int = 20) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values or []:
        normalized = str(value).strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            cleaned.append(normalized[:200])
        if len(cleaned) >= limit:
            break
    return cleaned


async def _load_style_profile(
    db: AsyncSession, user: User
) -> CreatorStyleProfile | None:
    return (
        await db.execute(
            select(CreatorStyleProfile).where(CreatorStyleProfile.user_id == user.id)
        )
    ).scalars().first()


async def get_style_profile(db: AsyncSession, user: User) -> dict:
    return _serialize_style(await _load_style_profile(db, user))


async def update_style_profile(
    db: AsyncSession, user: User, payload: StyleProfileUpdate
) -> dict:
    profile = await _load_style_profile(db, user)
    if not profile:
        profile = CreatorStyleProfile(user_id=user.id)
        db.add(profile)

    profile.tone = (payload.tone or "").strip()[:255]
    profile.language = (payload.language or "").strip()[:100]
    profile.audience_description = (payload.audience_description or "").strip()
    profile.technical_depth = _choice(
        payload.technical_depth, ALLOWED_DEPTHS, "intermediate"
    )
    profile.preferred_structures = _clean_allowed_list(
        payload.preferred_structures, ALLOWED_STRUCTURES
    )
    profile.avoid = _clean_free_list(payload.avoid)
    profile.posting_cadence = max(1, min(14, payload.posting_cadence))
    profile.preferred_formats = _clean_allowed_list(
        payload.preferred_formats, ALLOWED_FORMATS
    )
    profile.preferred_platforms = _clean_allowed_list(
        payload.preferred_platforms, ALLOWED_PLATFORMS
    )
    profile.reference_notes = (payload.reference_notes or "").strip()[:2000]

    await db.commit()
    return _serialize_style(profile)


def _style_prompt_block(style: CreatorStyleProfile | None) -> str:
    if not style:
        return "\n\nCREATOR STYLE:\nNo explicit style preferences configured."

    lines: list[str] = []
    if style.tone:
        lines.append(f"Tone: {style.tone}")
    if style.language:
        lines.append(f"Language: {style.language}")
    if style.audience_description:
        lines.append(f"Audience: {style.audience_description}")
    if style.technical_depth:
        lines.append(f"Technical depth: {style.technical_depth}")
    if style.preferred_structures:
        lines.append(
            "Preferred structures: " + ", ".join(style.preferred_structures)
        )
    if style.avoid:
        lines.append("Avoid: " + ", ".join(style.avoid))
    if style.reference_notes:
        lines.append(f"Additional notes: {style.reference_notes}")

    if not lines:
        return "\n\nCREATOR STYLE:\nNo explicit style preferences configured."
    return "\n\nCREATOR STYLE:\n" + "\n".join(lines)


def _style_hash(style: CreatorStyleProfile | None) -> str:
    if not style:
        return ""
    payload = {
        "tone": style.tone,
        "language": style.language,
        "audience_description": style.audience_description,
        "technical_depth": style.technical_depth,
        "preferred_structures": style.preferred_structures or [],
        "avoid": style.avoid or [],
        "posting_cadence": style.posting_cadence,
        "preferred_formats": style.preferred_formats or [],
        "preferred_platforms": style.preferred_platforms or [],
        "reference_notes": style.reference_notes,
    }
    return json.dumps(payload, sort_keys=True)



async def _get_or_fetch_video_transcript(
    db: AsyncSession, user: User, video: Video | None
) -> str | None:
    """Return a cached transcript, fetching it once from YouTube if possible."""
    if video is None or video.platform != "youtube":
        return None
    if not settings.YOUTUBE_TRANSCRIPT_ENABLED:
        return None
    if video.transcript:
        return video.transcript
    if video.transcript_fetched_at is not None:
        # A previous attempt found no captions; do not keep spending quota.
        return None

    social = await get_social_account(db, user.id, "youtube")
    if not social:
        return None

    try:
        await verify_quota_limit(db, user.id, planned_cost=250)
    except ValueError:
        logger.warning(
            "Skipping transcript fetch for video %s: quota exceeded", video.id
        )
        return None

    units = 0
    text: str | None = None
    try:
        access_token = await get_or_refresh_social_token(db, social)
        text, units = await fetch_video_transcript(access_token, video.external_id)
    except Exception:
        logger.exception("Failed to fetch transcript for video %s", video.id)

    if units:
        await log_api_quota(db, user.id, "youtube.captions", units)

    video.transcript = text
    video.transcript_fetched_at = _utcnow()
    db.add(video)
    await db.commit()
    return text


async def _load_script_context(
    db: AsyncSession, user: User, item_id: uuid.UUID
) -> tuple[
    ContentCalendarItem,
    ContentOpportunity | None,
    list[ContentOpportunityEvidence],
    list[Insight],
    Video | None,
    str | None,
]:
    item = (
        await db.execute(
            select(ContentCalendarItem).where(
                ContentCalendarItem.id == item_id,
                ContentCalendarItem.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not item:
        raise CalendarItemNotFoundError("Calendar item not found.")

    opportunity = None
    evidence: list[ContentOpportunityEvidence] = []
    if item.opportunity_id:
        opportunity = (
            await db.execute(
                select(ContentOpportunity).where(
                    ContentOpportunity.id == item.opportunity_id,
                    ContentOpportunity.creator_id == user.id,
                )
            )
        ).scalars().first()
        if opportunity:
            evidence = list(
                (
                    await db.execute(
                        select(ContentOpportunityEvidence)
                        .where(
                            ContentOpportunityEvidence.opportunity_id == opportunity.id
                        )
                        .order_by(ContentOpportunityEvidence.created_at.asc())
                        .limit(10)
                    )
                ).scalars().all()
            )

    insights: list[Insight] = []
    if opportunity and opportunity.analysis_id:
        insights = list(
            (
                await db.execute(
                    select(Insight)
                    .where(
                        Insight.analysis_id == opportunity.analysis_id,
                        Insight.type.in_(("question", "pain_point")),
                    )
                    .order_by(Insight.created_at.asc())
                    .limit(12)
                )
            ).scalars().all()
        )

    video = None
    if opportunity and opportunity.source_video_id:
        video = (
            await db.execute(
                select(Video).where(Video.id == opportunity.source_video_id)
            )
        ).scalars().first()

    transcript = await _get_or_fetch_video_transcript(db, user, video)
    return item, opportunity, evidence, insights, video, transcript


def _script_input_hash(
    item: ContentCalendarItem,
    opportunity: ContentOpportunity | None,
    evidence: list[ContentOpportunityEvidence],
    insights: list[Insight],
    style: CreatorStyleProfile | None,
    video: Video | None,
    transcript: str | None,
) -> str:
    parts = [
        str(item.id),
        item.title,
        item.angle,
        item.notes,
        item.content_context,
        item.format,
        item.length,
        item.platform,
        str(opportunity.id) if opportunity else "",
        opportunity.title if opportunity else "",
        opportunity.rationale if opportunity else "",
        opportunity.suggested_angle if opportunity else "",
        video.title if video else "",
        (video.description or "") if video else "",
        (video.url or "") if video else "",
        transcript or "",
    ]
    parts.extend(
        f"{insight.type}:{insight.title}:{insight.content}" for insight in insights
    )
    parts.extend(evidence_item.quote or "" for evidence_item in evidence)
    parts.append(_style_hash(style))
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _build_script_prompt(
    item: ContentCalendarItem,
    opportunity: ContentOpportunity | None,
    evidence: list[ContentOpportunityEvidence],
    insights: list[Insight],
    style: CreatorStyleProfile | None,
    video: Video | None,
    transcript: str | None,
) -> tuple[str, str]:
    question_lines = [
        f"- {insight.title}: {insight.content}"
        for insight in insights
        if insight.type == "question"
    ]
    pain_point_lines = [
        f"- {insight.title}: {insight.content}"
        for insight in insights
        if insight.type == "pain_point"
    ]
    evidence_lines = [
        f"- {evidence_item.quote}"
        for evidence_item in evidence
        if evidence_item.quote
    ]

    system_prompt = (
        "You are an experienced scriptwriter for a video creator. "
        "You are writing a NEW piece of content for the creator, not a description of an existing video.\n"
        "PRIMARY OBJECTIVE: address the audience questions and pain points in the brief, "
        "and deliver on the calendar item's topic and angle.\n"
        "Hard rules:\n"
        "- The analyzed video is REFERENCE CONTEXT only. Do not summarize, narrate, or recap it.\n"
        "- Do not open with 'In this video' or describe what the source video covers, "
        "unless the calendar item explicitly asks for a recap of that video.\n"
        "- Start with the audience's problem or question and make the new content useful on its own.\n"
        "- Use the reference video, transcript, and creator notes only to keep facts accurate "
        "and to supply relevant examples or context.\n"
        "- Never invent what the analyzed video says, statistics, comments, quotes, or audience claims.\n"
        "- If audience evidence is missing, do not imply audience demand; write from the topic and angle only.\n"
        "- Follow the creator's explicit style preferences when supplied, but never let style override facts or evidence.\n"
        "- The main script should be a coherent draft, not just an outline.\n"
        "- Structure the main script into 3 to 6 clearly labelled sections. Use short, plain-text headings.\n"
        "- Write each section as real paragraphs separated by blank lines. Do not return one dense block.\n"
        "- Use plain text only: no Markdown symbols, bullet characters, or numbered lists in the script body.\n"
        "- Return only valid JSON, with no Markdown wrapper or commentary.\n"
        "JSON shape:\n"
        "{\n"
        '  "working_title": "A strong working title",\n'
        '  "hook": "An opening that earns attention",\n'
        '  "body": "The full draft assembled from the sections",\n'
        '  "sections": [\n'
        '    {"heading": "Short section heading", "content": "One or more paragraphs."}\n'
        "  ],\n"
        '  "talking_points": ["point 1", "point 2"],\n'
        '  "examples": ["example or demonstration"],\n'
        '  "cta": "A clear call to action",\n'
        '  "caption": "Optional short caption",\n'
        '  "description": "Optional longer description",\n'
        '  "alt_titles": ["alternative title"]\n'
        "}"
    )

    objective_block = (
        "\n\nPRIMARY OBJECTIVE:\n"
        f'Write a new {item.format} titled "{item.title}".\n'
        f"Angle: {item.angle or '(not specified)'}\n"
        f"Notes: {item.notes or '(none)'}\n"
        "This is NOT a recap of the source video.\n"
        "Return 3 to 6 script sections, each with a short heading and paragraphs."
    )

    questions_block = (
        "\n\nAUDIENCE QUESTIONS TO ANSWER:\n" + "\n".join(question_lines)
        if question_lines
        else "\n\nAUDIENCE QUESTIONS TO ANSWER:\n(none extracted)"
    )
    pain_points_block = (
        "\n\nAUDIENCE PAIN POINTS TO ADDRESS:\n" + "\n".join(pain_point_lines)
        if pain_point_lines
        else "\n\nAUDIENCE PAIN POINTS TO ADDRESS:\n(none extracted)"
    )
    evidence_block = (
        "\n\nSUPPORTING COMMENTS:\n" + "\n".join(evidence_lines)
        if evidence_lines
        else "\n\nSUPPORTING COMMENTS:\n(none supplied — do not claim audience demand)"
    )

    video_block = ""
    if video:
        video_block = (
            "\n\nREFERENCE VIDEO (context only — do not summarize):\n"
            f"Title: {_strip_identifiers(video.title)}\n"
            f"Description: {_strip_identifiers(video.description or '(none)')}\n"
        )
        if transcript:
            video_block += f"Transcript excerpt:\n{transcript[:12000]}"
        else:
            video_block += "Transcript: (not available)"

    opportunity_block = ""
    if opportunity:
        opportunity_block = (
            "\n\nCONTENT OPPORTUNITY / BRIEF:\n"
            f"Title: {_strip_identifiers(opportunity.title)}\n"
            f"Rationale: {_strip_identifiers(opportunity.rationale)}\n"
            f"Suggested angle: {_strip_identifiers(opportunity.suggested_angle)}\n"
            f"Format: {opportunity.suggested_format}\n"
            f"Length: {opportunity.suggested_length}\n"
            f"Source video: {opportunity.source_video_title or 'Unknown'}"
        )

    context_block = (
        "\n\nCREATOR NOTES / VIDEO CONTEXT:\n"
        + (item.content_context or "(none)")
    )

    user_prompt = (
        "Write the new script/content brief described below.\n"
        f"{objective_block}"
        f"{questions_block}"
        f"{pain_points_block}"
        f"{evidence_block}"
        f"{opportunity_block}"
        f"{video_block}"
        f"{context_block}"
        f"{_style_prompt_block(style)}"
    )
    return user_prompt, system_prompt


def _parse_script_response(raw: str) -> ScriptContent:
    clean = (raw or "").strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    try:
        payload = json.loads(clean)
        content = ScriptContent.model_validate(payload)
    except Exception as exc:
        logger.warning("Script LLM response was not valid JSON: %s", exc)
        raise ScriptGenerationError(
            "The AI returned an unusable script. Please try again."
        ) from exc

    content.working_title = _strip_identifiers(content.working_title)
    content.hook = _strip_identifiers_preserving_paragraphs(content.hook)
    content.body = _strip_identifiers_preserving_paragraphs(content.body)
    content.cta = _strip_identifiers_preserving_paragraphs(content.cta)
    content.caption = _strip_identifiers_preserving_paragraphs(content.caption)
    content.description = _strip_identifiers_preserving_paragraphs(
        content.description
    )
    content.talking_points = [
        _strip_identifiers(str(item))
        for item in content.talking_points
        if _strip_identifiers(str(item))
    ]
    content.examples = [
        _strip_identifiers(str(item))
        for item in content.examples
        if _strip_identifiers(str(item))
    ]
    content.alt_titles = [
        _strip_identifiers(str(item))
        for item in content.alt_titles
        if _strip_identifiers(str(item))
    ]

    sections = _clean_sections(content.sections)
    if sections:
        # Sections are the structured source of truth; keep body as a plain
        # text export for older clients and copy/paste.
        content.body = _body_from_sections(sections)
    elif content.body:
        # Backward-compatible fallback for models that still return only body.
        sections = _sections_from_body(content.body)
    content.sections = [ScriptSection(**section) for section in sections]

    if not content.working_title or not content.body:
        raise ScriptGenerationError(
            "The AI returned an incomplete script. Please try again."
        )
    return content


async def get_current_script(
    db: AsyncSession, user: User, item_id: uuid.UUID
) -> dict:
    item = (
        await db.execute(
            select(ContentCalendarItem).where(
                ContentCalendarItem.id == item_id,
                ContentCalendarItem.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not item:
        raise CalendarItemNotFoundError("Calendar item not found.")

    script = (
        await db.execute(
            select(ContentScript)
            .where(
                ContentScript.calendar_item_id == item_id,
                ContentScript.creator_id == user.id,
            )
            .order_by(ContentScript.version.desc())
            .limit(1)
        )
    ).scalars().first()
    if not script:
        raise ScriptNotFoundError("No script has been generated for this item yet.")
    return _serialize_script(script)


async def list_scripts(
    db: AsyncSession, user: User, item_id: uuid.UUID
) -> list[dict]:
    item = (
        await db.execute(
            select(ContentCalendarItem).where(
                ContentCalendarItem.id == item_id,
                ContentCalendarItem.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not item:
        raise CalendarItemNotFoundError("Calendar item not found.")

    scripts = (
        await db.execute(
            select(ContentScript)
            .where(
                ContentScript.calendar_item_id == item_id,
                ContentScript.creator_id == user.id,
            )
            .order_by(ContentScript.version.desc())
        )
    ).scalars().all()
    return [_serialize_script(script) for script in scripts]


async def get_script(db: AsyncSession, user: User, script_id: uuid.UUID) -> dict:
    script = (
        await db.execute(
            select(ContentScript).where(
                ContentScript.id == script_id,
                ContentScript.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not script:
        raise ScriptNotFoundError("Script not found.")
    return _serialize_script(script)


async def update_script(
    db: AsyncSession, user: User, script_id: uuid.UUID, payload: ScriptUpdate
) -> dict:
    script = (
        await db.execute(
            select(ContentScript).where(
                ContentScript.id == script_id,
                ContentScript.creator_id == user.id,
            )
        )
    ).scalars().first()
    if not script:
        raise ScriptNotFoundError("Script not found.")

    data = payload.model_dump(exclude_unset=True)
    sections_provided = "sections" in data
    body_provided = "body" in data

    for key, value in data.items():
        if key in {"sections", "body"}:
            continue
        if key == "working_title":
            title = (value or "").strip()
            if not title:
                raise InvalidCalendarRequestError("A working title is required.")
            script.working_title = title[:255]
        elif key in {"talking_points", "examples", "alt_titles"}:
            setattr(
                script,
                key,
                [str(item).strip() for item in (value or []) if str(item).strip()],
            )
        elif key in {"hook", "cta", "caption", "description"}:
            setattr(script, key, value or "")

    if sections_provided:
        cleaned = _clean_sections(
            payload.sections or [], clean_identifiers=False
        )
        script.sections = cleaned
        script.body = _body_from_sections(cleaned)
    elif body_provided:
        # Backward-compatible path for clients that still edit one text block.
        script.body = (payload.body or "").strip()
        script.sections = _sections_from_body(script.body)

    script.user_edited_at = _utcnow()
    db.add(script)
    await db.commit()
    return _serialize_script(script)


async def generate_script(
    db: AsyncSession, user: User, item_id: uuid.UUID, force: bool = False
) -> tuple[dict, bool]:
    item, opportunity, evidence, insights, video, transcript = (
        await _load_script_context(db, user, item_id)
    )
    style = await _load_style_profile(db, user)
    input_hash = _script_input_hash(
        item, opportunity, evidence, insights, style, video, transcript
    )

    latest = (
        await db.execute(
            select(ContentScript)
            .where(
                ContentScript.calendar_item_id == item_id,
                ContentScript.creator_id == user.id,
            )
            .order_by(ContentScript.version.desc())
            .limit(1)
        )
    ).scalars().first()

    if latest and not force and latest.input_hash == input_hash:
        return _serialize_script(latest), True

    user_prompt, system_prompt = _build_script_prompt(
        item, opportunity, evidence, insights, style, video, transcript
    )

    try:
        raw = await generate_chat_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            json_mode=True,
        )
    except Exception as exc:
        logger.exception("Script generation model call failed")
        raise ScriptGenerationError(
            "Script generation is unavailable right now. Please try again."
        ) from exc

    content = _parse_script_response(raw)
    version = (latest.version + 1) if latest else 1

    script = ContentScript(
        calendar_item_id=item.id,
        creator_id=user.id,
        version=version,
        working_title=content.working_title[:255],
        hook=content.hook,
        body=content.body,
        sections=[section.model_dump() for section in content.sections],
        talking_points=content.talking_points,
        examples=content.examples,
        cta=content.cta,
        caption=content.caption,
        description=content.description,
        alt_titles=content.alt_titles,
        model=settings.GROQ_LLM_MODEL,
        input_hash=input_hash,
        generated_at=_utcnow(),
    )
    db.add(script)
    await db.commit()
    logger.info(
        "Generated script version %d for calendar item %s", version, item_id
    )
    return _serialize_script(script), False


