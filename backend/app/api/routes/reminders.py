from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, require_cron
from app.schemas.misc import ReminderRunResult
from app.services import reminders as svc

router = APIRouter(prefix="/api", tags=["reminders"])


@router.post(
    "/jobs/reminders", response_model=ReminderRunResult, dependencies=[Depends(require_cron)]
)
async def run_reminders(db: DbSession) -> ReminderRunResult:
    """Triggered by the GitHub Actions cron. Protected by the shared CRON_SECRET
    header (x-cron-secret) rather than a user JWT, since no user is in the loop."""
    return await svc.run_reminders(db)


@router.get("/reminders/history")
async def reminder_history(
    user: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=200)
) -> list[dict]:
    return await svc.reminder_history(db, user.id, limit)
