from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Meeting, TranscriptSegment
from app.schemas.misc import SearchHit
from app.services.embeddings import embeddings_service


async def search(db: AsyncSession, user_id: str, query: str, limit: int = 10) -> list[SearchHit]:
    """Cross-meeting search.

    Uses pgvector cosine similarity when embeddings are available, and falls back
    to keyword search otherwise so the feature works without an embedding key.
    """
    q = query.strip()
    if not q:
        return []

    vector = await embeddings_service.embed(q) if embeddings_service.is_configured() else None
    if vector is not None:
        hits = await _semantic(db, user_id, vector, limit)
        if hits:
            return hits
    return await _keyword(db, user_id, q, limit)


async def _semantic(
    db: AsyncSession, user_id: str, vector: list[float], limit: int
) -> list[SearchHit]:
    distance = TranscriptSegment.embedding.cosine_distance(vector)
    stmt = (
        select(
            TranscriptSegment.id,
            TranscriptSegment.meeting_id,
            Meeting.title,
            TranscriptSegment.speaker,
            TranscriptSegment.timestamp,
            TranscriptSegment.text,
            distance.label("distance"),
        )
        .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
        .where(Meeting.user_id == user_id, TranscriptSegment.embedding.isnot(None))
        .order_by(distance.asc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        SearchHit(
            segment_id=r[0],
            meeting_id=r[1],
            meeting_title=r[2],
            speaker=r[3],
            timestamp=r[4],
            text=r[5],
            score=round(1 - float(r[6]), 2),
            mode="semantic",
        )
        for r in rows
    ]


async def _keyword(db: AsyncSession, user_id: str, query: str, limit: int) -> list[SearchHit]:
    stmt = (
        select(TranscriptSegment, Meeting.title)
        .join(Meeting, Meeting.id == TranscriptSegment.meeting_id)
        .where(Meeting.user_id == user_id, TranscriptSegment.text.ilike(f"%{query}%"))
        .order_by(TranscriptSegment.ordinal.asc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        SearchHit(
            segment_id=seg.id,
            meeting_id=seg.meeting_id,
            meeting_title=title,
            speaker=seg.speaker,
            timestamp=seg.timestamp,
            text=seg.text,
            score=1.0,
            mode="keyword",
        )
        for seg, title in rows
    ]
