from dataclasses import dataclass, field


@dataclass
class RawCitation:
    segment_index: int


@dataclass
class RawInsight:
    text: str
    citations: list[RawCitation] = field(default_factory=list)


@dataclass
class RawActionItem:
    task: str
    assignee: str | None = None
    due_date: str | None = None
    citations: list[RawCitation] = field(default_factory=list)


@dataclass
class RawAnalysis:
    summary: list[RawInsight] = field(default_factory=list)
    decisions: list[RawInsight] = field(default_factory=list)
    follow_ups: list[RawInsight] = field(default_factory=list)
    action_items: list[RawActionItem] = field(default_factory=list)
