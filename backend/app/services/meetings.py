from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models import ActionItem, Meeting, TranscriptSegment
from app.schemas.common import Paginated, build_meta
from app.schemas.meeting import CreateMeetingIn, MeetingDetailOut, MeetingSummaryOut
from app.services.mappers import meeting_detail_out, meeting_summary_out


async def _load_detail(db: AsyncSession, meeting_id: str, user_id: str) -> Meeting:
    from app.models import Insight  # local import avoids cycle noise

    stmt = (
        select(Meeting)
        .where(Meeting.id == meeting_id, Meeting.user_id == user_id)
        .options(
            selectinload(Meeting.segments),
            selectinload(Meeting.insights).selectinload(Insight.citations),
            selectinload(Meeting.action_items).selectinload(ActionItem.citations),
        )
    )
    meeting = (await db.execute(stmt)).scalar_one_or_none()
    if meeting is None:
        raise AppError.not_found("Meeting not found")
    return meeting


async def create_meeting(
    db: AsyncSession, user_id: str, payload: CreateMeetingIn
) -> MeetingDetailOut:
    meeting = Meeting(
        user_id=user_id,
        title=payload.title,
        meeting_date=payload.meeting_date,
        participants=[str(p) for p in payload.participants],
    )
    for ordinal, seg in enumerate(payload.transcript):
        meeting.segments.append(
            TranscriptSegment(
                ordinal=ordinal, timestamp=seg.timestamp, speaker=seg.speaker, text=seg.text
            )
        )
    db.add(meeting)
    await db.commit()
    detail = await _load_detail(db, meeting.id, user_id)
    return meeting_detail_out(detail)


async def list_meetings(
    db: AsyncSession,
    user_id: str,
    page: int,
    limit: int,
    search: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Paginated[MeetingSummaryOut]:
    filters = [Meeting.user_id == user_id]
    if search:
        filters.append(Meeting.title.ilike(f"%{search}%"))
    if status:
        filters.append(Meeting.status == status)
    if date_from:
        filters.append(Meeting.meeting_date >= date_from)
    if date_to:
        filters.append(Meeting.meeting_date <= date_to)

    total = (
        await db.execute(select(func.count()).select_from(Meeting).where(*filters))
    ).scalar_one()

    rows = (
        (
            await db.execute(
                select(Meeting)
                .where(*filters)
                .order_by(Meeting.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    items: list[MeetingSummaryOut] = []
    for m in rows:
        seg_count = (
            await db.execute(
                select(func.count())
                .select_from(TranscriptSegment)
                .where(TranscriptSegment.meeting_id == m.id)
            )
        ).scalar_one()
        ai_count = (
            await db.execute(
                select(func.count()).select_from(ActionItem).where(ActionItem.meeting_id == m.id)
            )
        ).scalar_one()
        items.append(meeting_summary_out(m, seg_count, ai_count))

    return Paginated[MeetingSummaryOut](items=items, meta=build_meta(page, limit, total))


async def get_meeting(db: AsyncSession, user_id: str, meeting_id: str) -> MeetingDetailOut:
    detail = await _load_detail(db, meeting_id, user_id)
    return meeting_detail_out(detail)
