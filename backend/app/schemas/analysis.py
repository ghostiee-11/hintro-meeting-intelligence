from datetime import datetime

from pydantic import Field

from app.models import ActionItemStatus, InsightType
from app.schemas.common import CamelModel


class CitationOut(CamelModel):
    timestamp: str
    segment_index: int | None = None
    verified: bool = True


class InsightOut(CamelModel):
    id: str
    type: InsightType
    text: str
    grounding_score: float
    citations: list[CitationOut]


class ActionItemOut(CamelModel):
    id: str
    meeting_id: str
    task: str
    assignee: str | None = None
    status: ActionItemStatus
    due_date: datetime | None = None
    grounding_score: float
    source: str
    citations: list[CitationOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AnalysisResultOut(CamelModel):
    meeting_id: str
    summary: list[InsightOut]
    decisions: list[InsightOut]
    follow_ups: list[InsightOut]
    action_items: list[ActionItemOut]
    grounding_score: float
    dropped_count: int
    provider: str | None = None
