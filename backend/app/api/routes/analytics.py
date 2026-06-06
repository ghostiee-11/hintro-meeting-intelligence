from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.misc import AnalyticsOut
from app.services import analytics as svc

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
async def analytics_overview(user: CurrentUser, db: DbSession) -> AnalyticsOut:
    return await svc.overview(db, user.id)
