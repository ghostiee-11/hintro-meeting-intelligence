from app.schemas.common import CamelModel


class EvaluationOut(CamelModel):
    candidate_name: str
    email: str
    repository_url: str
    deployed_url: str
    external_integration: str
    features: list[str]


class HealthOut(CamelModel):
    status: str
    checks: dict[str, str]


class SearchHit(CamelModel):
    segment_id: str
    meeting_id: str
    meeting_title: str
    speaker: str
    timestamp: str
    text: str
    score: float
    mode: str


class AssigneeLoad(CamelModel):
    assignee: str
    open: int
    overdue: int


class ActivityPoint(CamelModel):
    date: str
    created: int


class AnalyticsTotals(CamelModel):
    meetings: int
    action_items: int
    overdue: int
    completed: int
    avg_grounding_score: float


class AnalyticsOut(CamelModel):
    totals: AnalyticsTotals
    status_distribution: dict[str, int]
    by_assignee: list[AssigneeLoad]
    recent_activity: list[ActivityPoint]


class ReminderDetail(CamelModel):
    action_item_id: str
    channel: str
    status: str
    error: str | None = None


class ReminderRunResult(CamelModel):
    overdue_count: int
    reminders_sent: int
    skipped: int
    failed: int
    channels: list[str]
    details: list[ReminderDetail]
