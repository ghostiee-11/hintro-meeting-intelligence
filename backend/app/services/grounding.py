"""Deterministic, LLM-free verification of AI output against the transcript.

The grounding guarantee is enforced here, by construction, not by trusting the model:
  1. A citation is verified only if its segment index resolves to a real segment.
  2. An insight or action item with zero verified citations is discarded entirely.
  3. A grounding score blends citation coverage with lexical overlap between the
     generated text and the cited segment text, so a real-but-irrelevant citation
     still scores low and is visibly flagged.

This is the system's anti-hallucination backbone.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.models import InsightType
from app.services.llm.schema import RawAnalysis, RawCitation

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "we",
    "i",
    "will",
    "should",
    "is",
    "are",
    "be",
    "this",
    "that",
    "it",
    "as",
    "at",
    "by",
    "our",
    "you",
    "they",
    "he",
    "she",
    "next",
    "have",
    "has",
    "was",
    "were",
    "do",
    "does",
    "about",
    "so",
}


@dataclass
class SegmentRef:
    index: int
    id: str
    timestamp: str
    text: str


@dataclass
class VerifiedCitation:
    segment_index: int
    timestamp: str
    transcript_segment_id: str
    verified: bool = True


@dataclass
class GroundedInsight:
    type: InsightType
    text: str
    grounding_score: float
    citations: list[VerifiedCitation]


@dataclass
class GroundedActionItem:
    task: str
    assignee: str | None
    due_date: datetime | None
    grounding_score: float
    citations: list[VerifiedCitation]


@dataclass
class GroundedAnalysis:
    insights: list[GroundedInsight] = field(default_factory=list)
    action_items: list[GroundedActionItem] = field(default_factory=list)
    dropped_count: int = 0
    overall_score: float = 0.0


class GroundingService:
    def ground(self, raw: RawAnalysis, segments: list[SegmentRef]) -> GroundedAnalysis:
        by_index = {s.index: s for s in segments}
        result = GroundedAnalysis()

        def ground_insights(items, insight_type: InsightType) -> None:
            for item in items:
                citations = self._verify(item.citations, by_index)
                if not citations:
                    result.dropped_count += 1
                    continue
                result.insights.append(
                    GroundedInsight(
                        type=insight_type,
                        text=item.text.strip(),
                        citations=citations,
                        grounding_score=self._score(
                            item.text, citations, by_index, len(item.citations)
                        ),
                    )
                )

        ground_insights(raw.summary, InsightType.SUMMARY)
        ground_insights(raw.decisions, InsightType.DECISION)
        ground_insights(raw.follow_ups, InsightType.FOLLOW_UP)

        for item in raw.action_items:
            citations = self._verify(item.citations, by_index)
            if not citations:
                result.dropped_count += 1
                continue
            result.action_items.append(
                GroundedActionItem(
                    task=item.task.strip(),
                    assignee=(item.assignee.strip() if item.assignee else None),
                    due_date=self._parse_date(item.due_date),
                    citations=citations,
                    grounding_score=self._score(
                        item.task, citations, by_index, len(item.citations)
                    ),
                )
            )

        scored = [x.grounding_score for x in result.insights + result.action_items]
        result.overall_score = round(sum(scored) / len(scored), 2) if scored else 0.0
        return result

    def _verify(
        self, raw: list[RawCitation], by_index: dict[int, SegmentRef]
    ) -> list[VerifiedCitation]:
        seen: set[int] = set()
        verified: list[VerifiedCitation] = []
        for c in raw:
            seg = by_index.get(c.segment_index)
            if seg is None or c.segment_index in seen:
                continue
            seen.add(c.segment_index)
            verified.append(
                VerifiedCitation(
                    segment_index=seg.index,
                    timestamp=seg.timestamp,
                    transcript_segment_id=seg.id,
                )
            )
        return verified

    def _score(
        self,
        text: str,
        verified: list[VerifiedCitation],
        by_index: dict[int, SegmentRef],
        claimed_count: int,
    ) -> float:
        coverage = 0.0 if claimed_count == 0 else min(1.0, len(verified) / claimed_count)
        text_tokens = self._tokens(text)
        best_overlap = 0.0
        for c in verified:
            seg = by_index.get(c.segment_index)
            if seg is None:
                continue
            best_overlap = max(best_overlap, self._containment(text_tokens, self._tokens(seg.text)))
        score = 0.5 * coverage + 0.5 * best_overlap
        return round(max(0.0, min(1.0, score)), 2)

    def _tokens(self, text: str) -> set[str]:
        cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        return {t for t in cleaned.split() if len(t) > 2 and t not in _STOPWORDS}

    def _containment(self, text_tokens: set[str], seg_tokens: set[str]) -> float:
        if not text_tokens:
            return 0.0
        hits = sum(1 for t in text_tokens if t in seg_tokens)
        return hits / len(text_tokens)

    def _parse_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        raw = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
        return None


grounding_service = GroundingService()
