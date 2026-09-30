"""Read-only aggregation queries backing the internal admin dashboard.

Everything here is SELECT-only. No endpoint in this module mutates data — the
admin surface is metrics-only in Phase 1.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import distinct, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.analysis.models import Analysis, AnalysisJob, Insight
from app.modules.comments.models import Comment
from app.modules.users.models import ApiQuotaUsage, SocialAccount, User
from app.modules.waitlist.models import WaitlistEntry
from app.modules.youtube.models import Channel, Video


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _midnight_utc() -> datetime:
    return _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


async def _count(db: AsyncSession, model) -> int:
    result = await db.execute(select(func.count()).select_from(model))
    return int(result.scalar() or 0)


async def _count_since(db: AsyncSession, model, since: datetime) -> int:
    result = await db.execute(
        select(func.count()).select_from(model).where(model.created_at >= since)
    )
    return int(result.scalar() or 0)


async def _sum_where(db: AsyncSession, stmt) -> int:
    result = await db.execute(stmt)
    return int(result.scalar() or 0)


async def _group_counts(db: AsyncSession, column) -> dict[str, int]:
    rows = (await db.execute(select(column, func.count()).group_by(column))).all()
    return {str(key): int(count) for key, count in rows}


async def _daily_counts(db: AsyncSession, model, since: datetime) -> dict:
    day = func.date_trunc("day", model.created_at)
    stmt = select(day, func.count()).where(model.created_at >= since).group_by(day)
    rows = (await db.execute(stmt)).all()
    return {row[0].date(): int(row[1]) for row in rows}


async def sync_admin_flags(db: AsyncSession) -> int:
    """Reconcile ``User.is_admin`` with the ``ADMIN_EMAILS`` allowlist.

    Promotes everyone on the list and demotes everyone off it, so the env var is
    the single source of truth. With an empty allowlist every admin is demoted
    (fail closed). Returns the number of rows changed.
    """
    allow = settings.admin_emails_list

    if allow:
        promote = await db.execute(
            update(User)
            .where(func.lower(User.email).in_(allow), User.is_admin.is_(False))
            .values(is_admin=True)
        )
        demote = await db.execute(
            update(User)
            .where(func.lower(User.email).notin_(allow), User.is_admin.is_(True))
            .values(is_admin=False)
        )
    else:
        demote = await db.execute(
            update(User).where(User.is_admin.is_(True)).values(is_admin=False)
        )
        promote = None

    await db.commit()
    return int((promote.rowcount if promote else 0) or 0) + int(demote.rowcount or 0)


async def get_overview(db: AsyncSession) -> dict:
    now = _utcnow()
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    total_users = await _count(db, User)
    active_users = await _sum_where(
        db, select(func.count()).select_from(User).where(User.is_active.is_(True))
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "new_users_7d": await _count_since(db, User, d7),
        "new_users_30d": await _count_since(db, User, d30),
        "plan_split": await _group_counts(db, User.plan),
        "waitlist_total": await _count(db, WaitlistEntry),
        "waitlist_7d": await _count_since(db, WaitlistEntry, d7),
        "waitlist_30d": await _count_since(db, WaitlistEntry, d30),
        "total_channels": await _count(db, Channel),
        "channels_by_platform": await _group_counts(db, Channel.platform),
        "total_videos": await _count(db, Video),
        "total_comments": await _count(db, Comment),
        "total_analyses": await _count(db, Analysis),
        "total_insights": await _count(db, Insight),
        "connected_accounts": await _group_counts(db, SocialAccount.provider),
    }


async def get_growth(db: AsyncSession, days: int) -> dict:
    days = max(1, min(days, 365))
    start = _start_of_day(_utcnow() - timedelta(days=days - 1))

    series = {
        "users": await _daily_counts(db, User, start),
        "waitlist": await _daily_counts(db, WaitlistEntry, start),
        "comments": await _daily_counts(db, Comment, start),
        "analyses": await _daily_counts(db, Analysis, start),
        "insights": await _daily_counts(db, Insight, start),
    }

    points = []
    for offset in range(days):
        day = (start + timedelta(days=offset)).date()
        points.append(
            {
                "date": day,
                **{name: values.get(day, 0) for name, values in series.items()},
            }
        )

    return {"days": days, "points": points}


async def get_funnel(db: AsyncSession) -> dict:
    signed_up = await _count(db, User)
    connected_provider = int(
        (await db.execute(select(func.count(distinct(SocialAccount.user_id))))).scalar() or 0
    )
    synced_video = int(
        (await db.execute(select(func.count(distinct(Channel.creator_id))))).scalar() or 0
    )
    ran_analysis = int(
        (await db.execute(select(func.count(distinct(AnalysisJob.user_id))))).scalar() or 0
    )
    generated_insights = int(
        (
            await db.execute(
                select(func.count(distinct(Channel.creator_id)))
                .select_from(Insight)
                .join(Analysis, Insight.analysis_id == Analysis.id)
                .join(Video, Analysis.video_id == Video.id)
                .join(Channel, Video.channel_id == Channel.id)
            )
        ).scalar()
        or 0
    )

    raw_steps = [
        ("signed_up", "Signed up", signed_up),
        ("connected_provider", "Connected a provider", connected_provider),
        ("synced_video", "Synced a video", synced_video),
        ("ran_analysis", "Ran an analysis", ran_analysis),
        ("generated_insights", "Generated insights", generated_insights),
    ]

    steps = []
    previous = None
    for key, label, count in raw_steps:
        if previous is None:
            conversion_from_previous = None
        else:
            conversion_from_previous = round(count / previous * 100, 1) if previous else 0.0
        steps.append(
            {
                "key": key,
                "label": label,
                "count": count,
                "conversion_from_previous": conversion_from_previous,
                "conversion_from_start": round(count / signed_up * 100, 1) if signed_up else 0.0,
            }
        )
        previous = count

    return {"steps": steps}


async def get_usage(db: AsyncSession, days: int) -> dict:
    days = max(1, min(days, 90))
    start = _start_of_day(_utcnow() - timedelta(days=days - 1))
    today = _midnight_utc()

    units_today = await _sum_where(
        db,
        select(func.sum(ApiQuotaUsage.units_used)).where(ApiQuotaUsage.called_at >= today),
    )
    units_window = await _sum_where(
        db,
        select(func.sum(ApiQuotaUsage.units_used)).where(ApiQuotaUsage.called_at >= start),
    )

    endpoint_rows = (
        await db.execute(
            select(ApiQuotaUsage.endpoint, func.sum(ApiQuotaUsage.units_used))
            .where(ApiQuotaUsage.called_at >= start)
            .group_by(ApiQuotaUsage.endpoint)
            .order_by(func.sum(ApiQuotaUsage.units_used).desc())
        )
    ).all()
    by_endpoint = [{"endpoint": endpoint, "units": int(units or 0)} for endpoint, units in endpoint_rows]

    day = func.date_trunc("day", ApiQuotaUsage.called_at)
    series_rows = (
        await db.execute(
            select(day, func.sum(ApiQuotaUsage.units_used))
            .where(ApiQuotaUsage.called_at >= start)
            .group_by(day)
        )
    ).all()
    series_map = {row[0].date(): int(row[1] or 0) for row in series_rows}
    series = []
    for offset in range(days):
        day_value = (start + timedelta(days=offset)).date()
        series.append({"date": day_value, "units": series_map.get(day_value, 0)})

    top_rows = (
        await db.execute(
            select(ApiQuotaUsage.user_id, User.email, func.sum(ApiQuotaUsage.units_used))
            .join(User, User.id == ApiQuotaUsage.user_id)
            .where(ApiQuotaUsage.called_at >= start)
            .group_by(ApiQuotaUsage.user_id, User.email)
            .order_by(func.sum(ApiQuotaUsage.units_used).desc())
            .limit(10)
        )
    ).all()
    top_consumers = [
        {"user_id": user_id, "email": email, "units": int(units or 0)}
        for user_id, email, units in top_rows
    ]

    return {
        "days": days,
        "units_today": units_today,
        "units_window": units_window,
        "by_endpoint": by_endpoint,
        "series": series,
        "top_consumers": top_consumers,
    }


async def get_jobs(db: AsyncSession, failure_limit: int = 20) -> dict:
    total = await _count(db, AnalysisJob)
    by_status = await _group_counts(db, AnalysisJob.status)

    completed = by_status.get("completed", 0)
    failed = by_status.get("failed", 0)
    finished = completed + failed
    success_rate = round(completed / finished * 100, 1) if finished else 0.0

    avg_duration = (
        await db.execute(
            select(func.avg(func.extract("epoch", AnalysisJob.completed_at - AnalysisJob.started_at))).where(
                AnalysisJob.completed_at.is_not(None),
                AnalysisJob.started_at.is_not(None),
            )
        )
    ).scalar()

    failures = (
        (
            await db.execute(
                select(AnalysisJob)
                .where(AnalysisJob.status == "failed")
                .order_by(AnalysisJob.created_at.desc())
                .limit(max(1, min(failure_limit, 100)))
            )
        )
        .scalars()
        .all()
    )

    return {
        "total": total,
        "by_status": by_status,
        "success_rate": success_rate,
        "avg_duration_seconds": round(float(avg_duration), 1) if avg_duration is not None else None,
        "recent_failures": [
            {
                "id": job.id,
                "video_id": job.video_id,
                "user_id": job.user_id,
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
                "last_error": job.last_error,
                "created_at": job.created_at,
            }
            for job in failures
        ],
    }


def _pagination(page: int, limit: int, total: int) -> dict:
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit if limit else 0,
    }


async def list_users(
    db: AsyncSession,
    page: int,
    limit: int,
    search: str | None = None,
    plan: str | None = None,
    is_active: bool | None = None,
) -> dict:
    page = max(1, page)
    limit = max(1, min(limit, 100))

    conditions = []
    if search:
        like = f"%{search.strip().lower()}%"
        conditions.append(
            func.lower(User.email).like(like)
            | func.lower(func.coalesce(User.full_name, "")).like(like)
        )
    if plan:
        conditions.append(User.plan == plan)
    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))

    count_stmt = select(func.count()).select_from(User)
    list_stmt = select(User)
    for condition in conditions:
        count_stmt = count_stmt.where(condition)
        list_stmt = list_stmt.where(condition)

    total = int((await db.execute(count_stmt)).scalar() or 0)
    users = (
        (
            await db.execute(
                list_stmt.order_by(User.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    ids = [user.id for user in users]
    connection_counts: dict = {}
    video_counts: dict = {}
    if ids:
        connection_rows = (
            await db.execute(
                select(SocialAccount.user_id, func.count())
                .where(SocialAccount.user_id.in_(ids))
                .group_by(SocialAccount.user_id)
            )
        ).all()
        connection_counts = {user_id: int(count) for user_id, count in connection_rows}

        video_rows = (
            await db.execute(
                select(Channel.creator_id, func.count(Video.id))
                .join(Video, Video.channel_id == Channel.id)
                .where(Channel.creator_id.in_(ids))
                .group_by(Channel.creator_id)
            )
        ).all()
        video_counts = {user_id: int(count) for user_id, count in video_rows}

    data = [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "plan": user.plan,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "connections": connection_counts.get(user.id, 0),
            "videos": video_counts.get(user.id, 0),
        }
        for user in users
    ]

    return {"data": data, "pagination": _pagination(page, limit, total)}


async def list_waitlist(
    db: AsyncSession,
    page: int,
    limit: int,
    search: str | None = None,
) -> dict:
    page = max(1, page)
    limit = max(1, min(limit, 100))

    count_stmt = select(func.count()).select_from(WaitlistEntry)
    list_stmt = select(WaitlistEntry)
    if search:
        like = f"%{search.strip().lower()}%"
        count_stmt = count_stmt.where(func.lower(WaitlistEntry.email).like(like))
        list_stmt = list_stmt.where(func.lower(WaitlistEntry.email).like(like))

    total = int((await db.execute(count_stmt)).scalar() or 0)
    entries = (
        (
            await db.execute(
                list_stmt.order_by(WaitlistEntry.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    return {"data": entries, "pagination": _pagination(page, limit, total)}
