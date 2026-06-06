from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.misc import SearchHit
from app.services import search as svc

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[SearchHit])
async def search(
    user: CurrentUser,
    db: DbSession,
    q: str = Query(..., description="Natural-language query"),
    limit: int = Query(10, ge=1, le=50),
) -> list[SearchHit]:
    return await svc.search(db, user.id, q, limit)
