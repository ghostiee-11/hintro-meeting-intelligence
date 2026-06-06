from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import cache
from app.models import ActionItem, ActionItemStatus, Meeting
from app.schemas.misc import (
    ActivityPoint,
    AnalyticsOut,
    AnalyticsTotals,
    AssigneeLoad,
)


async def overview(db: AsyncSession, user_id: str) -> AnalyticsOut:
    cache_key = f"analytics:{user_id}"
    cached = await cache.get_json(cache_key)
    if cached:
        return AnalyticsOut.model_validate(cached)

    now = datetime.now(UTC)

    # All action-item counts are scoped to the user's meetings via this join.
    def items_for_user():
        return (
            select(func.count())
            .select_from(ActionItem)
            .join(Meeting, Meeting.id == ActionItem.meeting_id)
            .where(Meeting.user_id == user_id)
        )

    async def count(stmt) -> int:
        return (await db.execute(stmt)).scalar_one()

    meetings = await count(
        select(func.count()).select_from(Meeting).where(Meeting.user_id == user_id)
    )
    total_items = await count(items_for_user())
    completed = await count(items_for_user().where(ActionItem.status == ActionItemStatus.COMPLETED))
    overdue = await count(
        items_for_user().where(
            ActionItem.status != ActionItemStatus.COMPLETED,
            ActionItem.due_date < now,
        )
    )
    avg_grounding = (
        await db.execute(
            select(func.avg(ActionItem.grounding_score))
            .select_from(ActionItem)
            .join(Meeting, Meeting.id == ActionItem.meeting_id)
            .where(Meeting.user_id == user_id, ActionItem.source == "AI")
        )
    ).scalar_one()

    grouped = (
        await db.execute(
            select(ActionItem.status, func.count())
            .join(Meeting, Meeting.id == ActionItem.meeting_id)
            .where(Meeting.user_id == user_id)
            .group_by(ActionItem.status)
        )
    ).all()
    status_distribution = {"PENDING": 0, "IN_PROGRESS": 0, "COMPLETED": 0}
    for status, count in grouped:
        status_distribution[status.value] = count

    by_assignee = await _assignee_breakdown(db, user_id, now)
    recent_activity = await _recent_activity(db, user_id)

    result = AnalyticsOut(
        totals=AnalyticsTotals(
            meetings=meetings,
            action_items=total_items,
            overdue=overdue,
            completed=completed,
            avg_grounding_score=round(float(avg_grounding or 0.0), 2),
        ),
        status_distribution=status_distribution,
        by_assignee=by_assignee,
        recent_activity=recent_activity,
    )
    await cache.set_json(cache_key, result.model_dump(by_alias=True, mode="json"), ttl_seconds=60)
    return result


async def _assignee_breakdown(db: AsyncSession, user_id: str, now: datetime) -> list[AssigneeLoad]:
    rows = (
        await db.execute(
            select(ActionItem.assignee, ActionItem.due_date)
            .join(Meeting, Meeting.id == ActionItem.meeting_id)
            .where(
                Meeting.user_id == user_id,
                ActionItem.status != ActionItemStatus.COMPLETED,
                ActionItem.assignee.isnot(None),
            )
        )
    ).all()
    agg: dict[str, dict[str, int]] = {}
    for assignee, due in rows:
        entry = agg.setdefault(assignee, {"open": 0, "overdue": 0})
        entry["open"] += 1
        if due is not None and due < now:
            entry["overdue"] += 1
    loads = [AssigneeLoad(assignee=a, open=v["open"], overdue=v["overdue"]) for a, v in agg.items()]
    loads.sort(key=lambda x: x.open, reverse=True)
    return loads[:10]


async def _recent_activity(db: AsyncSession, user_id: str) -> list[ActivityPoint]:
    since = (datetime.now(UTC) - timedelta(days=13)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    rows = (
        await db.execute(
            select(ActionItem.created_at)
            .join(Meeting, Meeting.id == ActionItem.meeting_id)
            .where(Meeting.user_id == user_id, ActionItem.created_at >= since)
        )
    ).all()
    buckets: dict[str, int] = {}
    for i in range(14):
        day = (since + timedelta(days=i)).date().isoformat()
        buckets[day] = 0
    for (created_at,) in rows:
        key = created_at.date().isoformat()
        if key in buckets:
            buckets[key] += 1
    return [ActivityPoint(date=d, created=c) for d, c in buckets.items()]
