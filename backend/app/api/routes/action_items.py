from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.models import ActionItemStatus
from app.schemas.action_item import CreateActionItemIn, UpdateStatusIn
from app.schemas.analysis import ActionItemOut
from app.schemas.common import Paginated
from app.services import action_items as svc

router = APIRouter(prefix="/api/action-items", tags=["action-items"])


@router.post("", response_model=ActionItemOut, status_code=201)
async def create_action_item(
    payload: CreateActionItemIn, user: CurrentUser, db: DbSession
) -> ActionItemOut:
    return await svc.create_action_item(db, user.id, payload)


@router.get("", response_model=Paginated[ActionItemOut])
async def list_action_items(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: ActionItemStatus | None = None,
    assignee: str | None = None,
    meeting_id: str | None = None,
) -> Paginated[ActionItemOut]:
    return await svc.list_action_items(
        db,
        user.id,
        page=page,
        limit=limit,
        status=status.value if status else None,
        assignee=assignee,
        meeting_id=meeting_id,
    )


@router.get("/overdue", response_model=Paginated[ActionItemOut])
async def overdue_action_items(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    assignee: str | None = None,
    meeting_id: str | None = None,
) -> Paginated[ActionItemOut]:
    return await svc.list_action_items(
        db,
        user.id,
        page=page,
        limit=limit,
        assignee=assignee,
        meeting_id=meeting_id,
        overdue=True,
    )


@router.patch("/{item_id}/status", response_model=ActionItemOut)
async def update_status(
    item_id: str, payload: UpdateStatusIn, user: CurrentUser, db: DbSession
) -> ActionItemOut:
    return await svc.update_status(db, user.id, item_id, payload.status)
