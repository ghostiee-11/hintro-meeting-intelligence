from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.redis import cache
from app.models import (
    ActionItem,
    Citation,
    Insight,
    InsightType,
    Meeting,
    MeetingStatus,
    TranscriptSegment,
)
from app.schemas.analysis import AnalysisResultOut
from app.services.embeddings import embeddings_service
from app.services.grounding import GroundedAnalysis, SegmentRef, grounding_service
from app.services.llm.prompt import IndexedSegment, build_analysis_prompt
from app.services.llm.service import llm_service
from app.services.mappers import action_item_out, insight_out

logger = get_logger("analysis")


async def _load_meeting(db: AsyncSession, user_id: str, meeting_id: str) -> Meeting | None:
    stmt = (
        select(Meeting)
        .where(Meeting.id == meeting_id, Meeting.user_id == user_id)
        .options(selectinload(Meeting.segments))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def analyze_stream(
    db: AsyncSession, user_id: str, meeting_id: str
) -> AsyncGenerator[dict[str, Any], None]:
    """Async generator yielding analysis progress, consumed by SSE and by analyze()."""
    yield {"stage": "loading", "message": "Loading meeting and transcript"}

    meeting = await _load_meeting(db, user_id, meeting_id)
    if meeting is None:
        yield {"stage": "error", "error": "Meeting not found"}
        return
    if not meeting.segments:
        yield {"stage": "error", "error": "Meeting has no transcript"}
        return

    meeting.status = MeetingStatus.ANALYZING
    await db.commit()

    segments = sorted(meeting.segments, key=lambda s: s.ordinal)
    seg_refs = [
        SegmentRef(index=s.ordinal, id=s.id, timestamp=s.timestamp, text=s.text) for s in segments
    ]

    try:
        yield {"stage": "analyzing", "message": "Generating insights with the LLM"}
        prompt = build_analysis_prompt(
            meeting.title,
            list(meeting.participants or []),
            [
                IndexedSegment(
                    index=s.ordinal, timestamp=s.timestamp, speaker=s.speaker, text=s.text
                )
                for s in segments
            ],
        )
        run = await llm_service.analyze(prompt)

        yield {
            "stage": "grounding",
            "message": "Verifying citations and scoring grounding",
            "provider": run.provider,
        }
        grounded = grounding_service.ground(run.analysis, seg_refs)

        yield {
            "stage": "persisting",
            "message": "Saving grounded insights",
            "provider": run.provider,
        }
        result = await _persist(db, meeting, grounded, run.provider)

        yield {"stage": "embedding", "message": "Indexing transcript for semantic search"}
        await _embed_segments(db, segments)

        await cache.delete(f"analytics:{user_id}")
        yield {
            "stage": "done",
            "message": "Analysis complete",
            "provider": run.provider,
            "result": result.model_dump(by_alias=True, mode="json"),
        }
    except AppError as exc:
        meeting.status = MeetingStatus.FAILED
        await db.commit()
        logger.error("analysis_failed", error=exc.message)
        yield {"stage": "error", "error": exc.message}
    except Exception as exc:  # noqa: BLE001
        meeting.status = MeetingStatus.FAILED
        await db.commit()
        logger.error("analysis_failed", error=str(exc))
        yield {"stage": "error", "error": "Analysis failed unexpectedly"}


async def analyze(db: AsyncSession, user_id: str, meeting_id: str) -> AnalysisResultOut:
    last_result: dict | None = None
    async for progress in analyze_stream(db, user_id, meeting_id):
        if progress["stage"] == "error":
            raise AppError.upstream(progress.get("error", "Analysis failed"))
        if progress.get("result"):
            last_result = progress["result"]
    if last_result is None:
        raise AppError.upstream("Analysis produced no result")
    return AnalysisResultOut.model_validate(last_result)


async def _persist(
    db: AsyncSession, meeting: Meeting, grounded: GroundedAnalysis, provider: str
) -> AnalysisResultOut:
    # Re-analysis replaces AI output but preserves manually created action items.
    await db.execute(delete(Insight).where(Insight.meeting_id == meeting.id))
    await db.execute(
        delete(ActionItem).where(ActionItem.meeting_id == meeting.id, ActionItem.source == "AI")
    )

    created_insights: list[Insight] = []
    for ins in grounded.insights:
        insight = Insight(
            meeting_id=meeting.id,
            type=ins.type,
            text=ins.text,
            grounding_score=ins.grounding_score,
            citations=[
                Citation(
                    transcript_segment_id=c.transcript_segment_id,
                    timestamp=c.timestamp,
                    segment_index=c.segment_index,
                    verified=True,
                )
                for c in ins.citations
            ],
        )
        db.add(insight)
        created_insights.append(insight)

    created_items: list[ActionItem] = []
    for ai in grounded.action_items:
        item = ActionItem(
            meeting_id=meeting.id,
            task=ai.task,
            assignee=ai.assignee,
            due_date=ai.due_date,
            grounding_score=ai.grounding_score,
            source="AI",
            citations=[
                Citation(
                    transcript_segment_id=c.transcript_segment_id,
                    timestamp=c.timestamp,
                    segment_index=c.segment_index,
                    verified=True,
                )
                for c in ai.citations
            ],
        )
        db.add(item)
        created_items.append(item)

    meeting.status = MeetingStatus.ANALYZED
    await db.commit()

    # Reload citations for clean serialization.
    for ins in created_insights:
        await db.refresh(ins, attribute_names=["citations"])
    for item in created_items:
        await db.refresh(item, attribute_names=["citations"])

    insights = [insight_out(i) for i in created_insights]
    return AnalysisResultOut(
        meeting_id=meeting.id,
        summary=[i for i in insights if i.type == InsightType.SUMMARY],
        decisions=[i for i in insights if i.type == InsightType.DECISION],
        follow_ups=[i for i in insights if i.type == InsightType.FOLLOW_UP],
        action_items=[action_item_out(a) for a in created_items],
        grounding_score=round(grounded.overall_score, 2),
        dropped_count=grounded.dropped_count,
        provider=provider,
    )


async def _embed_segments(db: AsyncSession, segments: list[TranscriptSegment]) -> None:
    if not embeddings_service.is_configured():
        return
    try:
        for seg in segments:
            vector = await embeddings_service.embed(f"{seg.speaker}: {seg.text}")
            if vector is not None:
                seg.embedding = vector
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("embedding_persist_failed", error=str(exc))
        await db.rollback()
