import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUser, DbSession, rate_limit
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.schemas.analysis import AnalysisResultOut
from app.services import analysis as svc

router = APIRouter(prefix="/api/meetings", tags=["analysis"])


@router.post(
    "/{meeting_id}/analyze",
    response_model=AnalysisResultOut,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def analyze_meeting(meeting_id: str, user: CurrentUser, db: DbSession) -> AnalysisResultOut:
    return await svc.analyze(db, user.id, meeting_id)


@router.get("/{meeting_id}/analyze/stream")
async def analyze_meeting_stream(meeting_id: str, token: str = Query(...)) -> StreamingResponse:
    """SSE streaming variant. EventSource cannot send Authorization headers, so the
    JWT is passed as a query token and verified manually. Opens its own DB session
    for the lifetime of the stream."""
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AppError.unauthorized("Invalid token")

    async def event_generator():
        async with SessionLocal() as db:
            try:
                async for progress in svc.analyze_stream(db, user_id, meeting_id):
                    yield f"data: {json.dumps(progress)}\n\n"
            except Exception as exc:  # noqa: BLE001
                yield f"data: {json.dumps({'stage': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
