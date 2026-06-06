from fastapi import APIRouter, Request

from app.core.deps import DbSession
from app.services.integrations.telegram import telegram_service
from app.services.reminders import handle_telegram_callback
from app.services.telegram_bot import handle_message

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, db: DbSession) -> dict:
    """Receives Telegram updates.

    - Button taps (callback_query) update an action item's status (two-way reminders).
    - Text messages and document uploads are handled by the conversational assistant:
      chat answers grounded in the user's data, and logging a meeting from a pasted
      transcript or an uploaded file.

    Returns the raw {ok: true} Telegram expects (excluded from the response envelope).
    """
    update = await request.json()

    callback = update.get("callback_query")
    if callback and callback.get("data"):
        result = await handle_telegram_callback(db, callback["data"])
        await telegram_service.answer_callback(callback["id"], result)
        msg = callback.get("message")
        if msg:
            await telegram_service.edit_message(
                msg["chat"]["id"], msg["message_id"], f"Status updated: {result}"
            )
        return {"ok": True}

    message = update.get("message")
    if message:
        await handle_message(db, message)

    return {"ok": True}
