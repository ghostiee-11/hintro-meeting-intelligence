from dataclasses import dataclass
from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("telegram")


@dataclass
class ReminderTarget:
    id: str
    task: str
    assignee: str | None
    due_date: datetime | None


@dataclass
class SendResult:
    ok: bool
    payload: str
    error: str | None = None


class TelegramService:
    """Telegram Bot API integration, actively used by the reminder workflow.

    Sends a formatted reminder with inline buttons so a user can change an action
    item's status directly from the chat (two-way integration).
    """

    def __init__(self) -> None:
        self._token = settings.telegram_bot_token
        self._chat_id = settings.telegram_chat_id

    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    def _format(self, item: ReminderTarget) -> str:
        due = item.due_date.date().isoformat() if item.due_date else "unspecified"
        return (
            f"*Reminder:* {item.task}\n"
            f"*Assigned To:* {item.assignee or 'Unassigned'}\n"
            f"*Due Date:* {due}"
        )

    async def send_reminder(self, item: ReminderTarget) -> SendResult:
        payload = {
            "chat_id": self._chat_id,
            "text": self._format(item),
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "Mark In Progress",
                            "callback_data": f"status:{item.id}:IN_PROGRESS",
                        },
                        {"text": "Mark Complete", "callback_data": f"status:{item.id}:COMPLETED"},
                    ]
                ]
            },
        }
        return await self._call("sendMessage", payload)

    async def answer_callback(self, callback_query_id: str, text: str) -> None:
        await self._call(
            "answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text}
        )

    async def edit_message(self, chat_id: int, message_id: int, text: str) -> None:
        await self._call(
            "editMessageText",
            {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"},
        )

    async def _call(self, method: str, body: dict) -> SendResult:
        import json

        payload_str = json.dumps(body)
        if not self.is_configured():
            return SendResult(ok=False, payload=payload_str, error="Telegram not configured")
        url = f"https://api.telegram.org/bot{self._token}/{method}"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=body)
                data = resp.json()
            if not data.get("ok"):
                return SendResult(ok=False, payload=payload_str, error=data.get("description"))
            return SendResult(ok=True, payload=payload_str)
        except Exception as exc:  # noqa: BLE001
            return SendResult(ok=False, payload=payload_str, error=str(exc))


telegram_service = TelegramService()
