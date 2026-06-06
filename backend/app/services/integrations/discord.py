import json

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.integrations.telegram import ReminderTarget, SendResult

logger = get_logger("discord")


class DiscordService:
    """Discord webhook integration, actively used by the reminder workflow.

    Sends a rich embed for each overdue action item.
    """

    def __init__(self) -> None:
        self._webhook_url = settings.discord_webhook_url

    def is_configured(self) -> bool:
        return bool(self._webhook_url)

    async def send_reminder(self, item: ReminderTarget) -> SendResult:
        due = item.due_date.date().isoformat() if item.due_date else "unspecified"
        body = {
            "username": "Hintro Reminders",
            "embeds": [
                {
                    "title": "Overdue Action Item",
                    "color": 0xEF4444,
                    "fields": [
                        {"name": "Task", "value": item.task},
                        {
                            "name": "Assigned To",
                            "value": item.assignee or "Unassigned",
                            "inline": True,
                        },
                        {"name": "Due Date", "value": due, "inline": True},
                    ],
                    "footer": {"text": "Hintro Meeting Intelligence"},
                }
            ],
        }
        payload_str = json.dumps(body)
        if not self.is_configured():
            return SendResult(ok=False, payload=payload_str, error="Discord not configured")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(self._webhook_url, json=body)
            if resp.status_code >= 300:
                return SendResult(
                    ok=False, payload=payload_str, error=f"Discord responded {resp.status_code}"
                )
            return SendResult(ok=True, payload=payload_str)
        except Exception as exc:  # noqa: BLE001
            return SendResult(ok=False, payload=payload_str, error=str(exc))


discord_service = DiscordService()
