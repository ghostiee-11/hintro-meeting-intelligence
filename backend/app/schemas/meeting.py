from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.models import MeetingStatus
from app.schemas.analysis import ActionItemOut, InsightOut
from app.schemas.common import CamelModel


class TranscriptSegmentIn(CamelModel):
    timestamp: str = Field(min_length=1)
    speaker: str = Field(min_length=1)
    text: str = Field(min_length=1)


class CreateMeetingIn(CamelModel):
    title: str = Field(min_length=1)
    participants: list[EmailStr] = Field(default_factory=list)
    meeting_date: datetime
    transcript: list[TranscriptSegmentIn] = Field(min_length=1)

    @field_validator("transcript")
    @classmethod
    def non_empty(cls, v: list[TranscriptSegmentIn]) -> list[TranscriptSegmentIn]:
        if not v:
            raise ValueError("At least one transcript segment is required")
        return v


class TranscriptSegmentOut(CamelModel):
    id: str
    ordinal: int
    timestamp: str
    speaker: str
    text: str


class MeetingSummaryOut(CamelModel):
    id: str
    title: str
    meeting_date: datetime
    participants: list[str]
    status: MeetingStatus
    segment_count: int = 0
    action_item_count: int = 0
    created_at: datetime


class MeetingDetailOut(MeetingSummaryOut):
    transcript: list[TranscriptSegmentOut]
    insights: list[InsightOut]
    action_items: list[ActionItemOut]
