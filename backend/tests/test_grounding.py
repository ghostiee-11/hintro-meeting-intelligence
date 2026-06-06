"""Tests for the deterministic grounding engine: the anti-hallucination backbone."""

from app.models import InsightType
from app.services.grounding import GroundingService, SegmentRef
from app.services.llm.schema import RawActionItem, RawAnalysis, RawCitation, RawInsight

service = GroundingService()

SEGMENTS = [
    SegmentRef(index=0, id="seg-0", timestamp="00:10", text="We should launch next Friday."),
    SegmentRef(index=1, id="seg-1", timestamp="00:20", text="I will prepare release notes."),
]


def _analysis(**kwargs) -> RawAnalysis:
    base = {"summary": [], "decisions": [], "follow_ups": [], "action_items": []}
    base.update(kwargs)
    return RawAnalysis(**base)


def test_keeps_insight_with_valid_citation_and_resolves_segment():
    raw = _analysis(
        summary=[RawInsight(text="Team plans to launch next Friday.", citations=[RawCitation(0)])]
    )
    result = service.ground(raw, SEGMENTS)
    assert len(result.insights) == 1
    assert result.insights[0].citations[0].transcript_segment_id == "seg-0"
    assert result.insights[0].citations[0].verified is True
    assert result.dropped_count == 0


def test_drops_fabricated_citation_to_nonexistent_segment():
    raw = _analysis(summary=[RawInsight(text="Imaginary point.", citations=[RawCitation(99)])])
    result = service.ground(raw, SEGMENTS)
    assert result.insights == []
    assert result.dropped_count == 1


def test_discards_insight_with_zero_citations():
    raw = _analysis(decisions=[RawInsight(text="Ungrounded decision.", citations=[])])
    result = service.ground(raw, SEGMENTS)
    assert result.insights == []
    assert result.dropped_count == 1


def test_drops_only_invalid_citations_and_penalizes_score():
    raw = _analysis(
        summary=[RawInsight(text="Launch next Friday.", citations=[RawCitation(0), RawCitation(42)])]
    )
    result = service.ground(raw, SEGMENTS)
    assert len(result.insights) == 1
    assert len(result.insights[0].citations) == 1
    assert result.insights[0].grounding_score < 1.0


def test_higher_score_when_text_overlaps_cited_segment():
    raw = _analysis(summary=[RawInsight(text="prepare release notes", citations=[RawCitation(1)])])
    result = service.ground(raw, SEGMENTS)
    assert result.insights[0].grounding_score > 0.5


def test_action_item_kept_with_assignee_and_due_date():
    raw = _analysis(
        action_items=[
            RawActionItem(
                task="Prepare release notes",
                assignee="Alice",
                due_date="2026-05-25",
                citations=[RawCitation(1)],
            )
        ]
    )
    result = service.ground(raw, SEGMENTS)
    assert len(result.action_items) == 1
    assert result.action_items[0].assignee == "Alice"
    assert result.action_items[0].due_date is not None
    assert result.action_items[0].due_date.year == 2026


def test_invalid_due_date_becomes_none():
    raw = _analysis(
        action_items=[RawActionItem(task="Do thing", due_date="not-a-date", citations=[RawCitation(0)])]
    )
    result = service.ground(raw, SEGMENTS)
    assert result.action_items[0].due_date is None


def test_insight_types_assigned_correctly():
    raw = _analysis(
        summary=[RawInsight(text="launch friday", citations=[RawCitation(0)])],
        decisions=[RawInsight(text="release notes", citations=[RawCitation(1)])],
    )
    result = service.ground(raw, SEGMENTS)
    types = {i.type for i in result.insights}
    assert InsightType.SUMMARY in types
    assert InsightType.DECISION in types
