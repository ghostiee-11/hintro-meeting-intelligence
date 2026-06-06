from datetime import datetime

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.models import MeetingStatus
from app.schemas.common import Paginated
from app.schemas.meeting import CreateMeetingIn, MeetingDetailOut, MeetingSummaryOut
from app.services import meetings as svc

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.post("", response_model=MeetingDetailOut, status_code=201)
async def create_meeting(
    payload: CreateMeetingIn, user: CurrentUser, db: DbSession
) -> MeetingDetailOut:
    return await svc.create_meeting(db, user.id, payload)


@router.get("", response_model=Paginated[MeetingSummaryOut])
async def list_meetings(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status: MeetingStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Paginated[MeetingSummaryOut]:
    return await svc.list_meetings(
        db,
        user.id,
        page=page,
        limit=limit,
        search=search,
        status=status.value if status else None,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{meeting_id}", response_model=MeetingDetailOut)
async def get_meeting(meeting_id: str, user: CurrentUser, db: DbSession) -> MeetingDetailOut:
    return await svc.get_meeting(db, user.id, meeting_id)
