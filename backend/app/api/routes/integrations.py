from fastapi import APIRouter, Request

from app.core.deps import DbSession
from app.services.integrations.telegram import telegram_service
from app.services.reminders import handle_telegram_callback

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, db: DbSession) -> dict:
    """Receives Telegram updates. When a user taps a reminder button, the callback
    data (status:<id>:<STATUS>) updates the action item and confirms in the chat,
    making the integration genuinely two-way. Returns the raw {ok: true} Telegram
    expects (this route is excluded from the response envelope)."""
    update = await request.json()
    callback = update.get("callback_query")
    if not callback or not callback.get("data"):
        return {"ok": True}

    message = await handle_telegram_callback(db, callback["data"])
    await telegram_service.answer_callback(callback["id"], message)

    msg = callback.get("message")
    if msg:
        await telegram_service.edit_message(
            msg["chat"]["id"], msg["message_id"], f"Status updated: {message}"
        )
    return {"ok": True}
