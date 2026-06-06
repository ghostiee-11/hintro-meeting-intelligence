"""Pure ORM -> Pydantic schema mappers. Assumes relationships are eager-loaded."""

from app.models import ActionItem, Citation, Insight, Meeting, TranscriptSegment
from app.schemas.analysis import ActionItemOut, CitationOut, InsightOut
from app.schemas.meeting import MeetingDetailOut, MeetingSummaryOut, TranscriptSegmentOut


def citation_out(c: Citation) -> CitationOut:
    return CitationOut(timestamp=c.timestamp, segment_index=c.segment_index, verified=c.verified)


def insight_out(i: Insight) -> InsightOut:
    return InsightOut(
        id=i.id,
        type=i.type,
        text=i.text,
        grounding_score=round(i.grounding_score, 2),
        citations=[citation_out(c) for c in i.citations],
    )


def action_item_out(a: ActionItem) -> ActionItemOut:
    return ActionItemOut(
        id=a.id,
        meeting_id=a.meeting_id,
        task=a.task,
        assignee=a.assignee,
        status=a.status,
        due_date=a.due_date,
        grounding_score=round(a.grounding_score, 2),
        source=a.source,
        citations=[citation_out(c) for c in a.citations],
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def segment_out(s: TranscriptSegment) -> TranscriptSegmentOut:
    return TranscriptSegmentOut(
        id=s.id, ordinal=s.ordinal, timestamp=s.timestamp, speaker=s.speaker, text=s.text
    )


def meeting_summary_out(
    m: Meeting, segment_count: int, action_item_count: int
) -> MeetingSummaryOut:
    return MeetingSummaryOut(
        id=m.id,
        title=m.title,
        meeting_date=m.meeting_date,
        participants=list(m.participants or []),
        status=m.status,
        segment_count=segment_count,
        action_item_count=action_item_count,
        created_at=m.created_at,
    )


def meeting_detail_out(m: Meeting) -> MeetingDetailOut:
    segments = sorted(m.segments, key=lambda s: s.ordinal)
    return MeetingDetailOut(
        id=m.id,
        title=m.title,
        meeting_date=m.meeting_date,
        participants=list(m.participants or []),
        status=m.status,
        segment_count=len(segments),
        action_item_count=len(m.action_items),
        created_at=m.created_at,
        transcript=[segment_out(s) for s in segments],
        insights=[insight_out(i) for i in m.insights],
        action_items=[
            action_item_out(a) for a in sorted(m.action_items, key=lambda a: a.created_at)
        ],
    )
