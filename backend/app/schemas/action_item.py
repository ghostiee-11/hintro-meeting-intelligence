from datetime import datetime

from pydantic import Field

from app.models import ActionItemStatus
from app.schemas.common import CamelModel


class CreateActionItemIn(CamelModel):
    meeting_id: str
    task: str = Field(min_length=1)
    assignee: str | None = None
    due_date: datetime | None = None


class UpdateStatusIn(CamelModel):
    status: ActionItemStatus


class ReminderLogOut(CamelModel):
    id: str
    action_item_id: str
    channel: str
    status: str
    error: str | None = None
    sent_at: datetime
