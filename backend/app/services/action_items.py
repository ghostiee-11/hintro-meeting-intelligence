from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.redis import cache
from app.models import ActionItem, ActionItemStatus, Meeting
from app.schemas.action_item import CreateActionItemIn
from app.schemas.analysis import ActionItemOut
from app.schemas.common import Paginated, build_meta
from app.services.mappers import action_item_out


async def _owned_item(db: AsyncSession, user_id: str, item_id: str) -> ActionItem:
    stmt = (
        select(ActionItem)
        .join(Meeting, Meeting.id == ActionItem.meeting_id)
        .where(ActionItem.id == item_id, Meeting.user_id == user_id)
        .options(selectinload(ActionItem.citations))
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if item is None:
        raise AppError.not_found("Action item not found")
    return item


async def create_action_item(
    db: AsyncSession, user_id: str, payload: CreateActionItemIn
) -> ActionItemOut:
    meeting = (
        await db.execute(
            select(Meeting).where(Meeting.id == payload.meeting_id, Meeting.user_id == user_id)
        )
    ).scalar_one_or_none()
    if meeting is None:
        raise AppError.not_found("Meeting not found")

    item = ActionItem(
        meeting_id=payload.meeting_id,
        task=payload.task,
        assignee=payload.assignee,
        due_date=payload.due_date,
        source="MANUAL",
        grounding_score=0.0,
    )
    db.add(item)
    await db.commit()
    await cache.delete(f"analytics:{user_id}")
    fresh = await _owned_item(db, user_id, item.id)
    return action_item_out(fresh)


async def update_status(
    db: AsyncSession, user_id: str, item_id: str, status: ActionItemStatus
) -> ActionItemOut:
    item = await _owned_item(db, user_id, item_id)
    item.status = status
    await db.commit()
    await cache.delete(f"analytics:{user_id}")
    fresh = await _owned_item(db, user_id, item_id)
    return action_item_out(fresh)


async def list_action_items(
    db: AsyncSession,
    user_id: str,
    page: int,
    limit: int,
    status: str | None = None,
    assignee: str | None = None,
    meeting_id: str | None = None,
    overdue: bool = False,
) -> Paginated[ActionItemOut]:
    filters = [Meeting.user_id == user_id]
    if overdue:
        filters.append(ActionItem.status != ActionItemStatus.COMPLETED)
        filters.append(ActionItem.due_date < datetime.now(UTC))
    if status:
        filters.append(ActionItem.status == status)
    if assignee:
        filters.append(ActionItem.assignee.ilike(assignee))
    if meeting_id:
        filters.append(ActionItem.meeting_id == meeting_id)

    base = select(ActionItem).join(Meeting, Meeting.id == ActionItem.meeting_id).where(*filters)

    total = (
        await db.execute(
            select(func.count())
            .select_from(ActionItem)
            .join(Meeting, Meeting.id == ActionItem.meeting_id)
            .where(*filters)
        )
    ).scalar_one()

    order = ActionItem.due_date.asc() if overdue else ActionItem.created_at.desc()
    rows = (
        (
            await db.execute(
                base.options(selectinload(ActionItem.citations))
                .order_by(order)
                .offset((page - 1) * limit)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    items = [action_item_out(a) for a in rows]
    return Paginated[ActionItemOut](items=items, meta=build_meta(page, limit, total))
