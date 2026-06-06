"""Conversational Telegram assistant for Hintro, powered by Groq.

Capabilities:
  - Chat: answers questions grounded in the owner's meetings and action items.
  - Log a meeting: paste a transcript or upload a .txt/.vtt/.srt file and the bot
    creates the meeting, runs grounded analysis, and replies with the results.
  - Commands: /start, /help, /meetings, /overdue.

The bot acts on behalf of a single configured Hintro account (TELEGRAM_OWNER_EMAIL).
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.models import ActionItem, ActionItemStatus, Meeting, User
from app.schemas.meeting import CreateMeetingIn, TranscriptSegmentIn
from app.services import meetings as meetings_svc
from app.services.analysis import analyze
from app.services.integrations.telegram import telegram_service
from app.services.transcript_parse import parse_transcript

logger = get_logger("telegram_bot")

HELP = (
    "I am your Hintro meeting assistant.\n\n"
    "What I can do:\n"
    "- Log a meeting: paste a transcript or upload a .txt/.vtt/.srt file and I will "
    "analyze it into grounded summaries, decisions, and action items.\n"
    "- Answer questions about your meetings and action items, e.g. 'what is overdue?', "
    "'summarize the last meeting', 'what did we decide about the launch?'.\n"
    "- Reminders: tap the buttons on overdue reminders to update status.\n\n"
    "Commands: /meetings, /overdue, /help"
)


async def get_owner(db: AsyncSession) -> User | None:
    user = (
        await db.execute(select(User).where(User.email == settings.telegram_owner_email))
    ).scalar_one_or_none()
    if user:
        return user
    return (
        await db.execute(select(User).order_by(User.created_at.asc()).limit(1))
    ).scalar_one_or_none()


def _looks_like_transcript(text: str) -> bool:
    lines = [line_ for line_ in text.splitlines() if line_.strip()]
    if "-->" in text and len(lines) >= 2:
        return True
    if len(lines) < 3:
        return False
    import re

    speaker_lines = sum(
        1
        for line_ in lines
        if re.match(r"^\s*(\[?\d{1,2}:\d{2}.*\]?\s*)?[A-Za-z][\w .'-]{0,39}:\s+", line_)
    )
    return speaker_lines >= 2


async def _build_context(db: AsyncSession, user_id: str) -> str:
    meetings = (
        (
            await db.execute(
                select(Meeting)
                .where(Meeting.user_id == user_id)
                .order_by(Meeting.created_at.desc())
                .limit(5)
                .options(selectinload(Meeting.insights), selectinload(Meeting.action_items))
            )
        )
        .scalars()
        .all()
    )
    if not meetings:
        return "The user has no meetings yet."

    now = datetime.now(UTC)
    parts: list[str] = []
    for m in meetings:
        summary = [i.text for i in m.insights if i.type.value == "SUMMARY"][:3]
        decisions = [i.text for i in m.insights if i.type.value == "DECISION"][:3]
        lines = [f"Meeting: {m.title} ({m.meeting_date.date()})"]
        if summary:
            lines.append("  Summary: " + "; ".join(summary))
        if decisions:
            lines.append("  Decisions: " + "; ".join(decisions))
        for a in m.action_items[:6]:
            due = a.due_date.date().isoformat() if a.due_date else "no due date"
            overdue = (
                " OVERDUE"
                if a.due_date and a.due_date < now and a.status != ActionItemStatus.COMPLETED
                else ""
            )
            who = a.assignee or "unassigned"
            lines.append(f"  Action: {a.task} [{who}, {a.status.value}, due {due}{overdue}]")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


async def _groq_reply(user_text: str, context: str) -> str:
    if not settings.groq_api_key:
        return "The assistant is not configured (no Groq key)."
    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=settings.groq_api_key)
        system = (
            "You are Hintro, a concise, friendly meeting-intelligence assistant on Telegram. "
            "Answer using ONLY the context about the user's meetings and action items below. "
            "If the answer is not in the context, say so briefly. Keep replies under 120 words, "
            "plain text (no markdown headers). To log a new meeting, tell the user to paste a "
            "transcript or upload a .txt/.vtt/.srt file.\n\nCONTEXT:\n" + context
        )
        completion = await client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
        )
        return completion.choices[0].message.content or "Sorry, I could not generate a reply."
    except Exception as exc:  # noqa: BLE001
        logger.warning("groq_reply_failed", error=str(exc))
        return "Sorry, I hit an error answering that. Try again in a moment."


async def _log_meeting(db: AsyncSession, user: User, raw: str, title: str | None) -> str:
    segments = parse_transcript(raw)
    if not segments:
        return "I couldn't find any transcript lines. Send lines like 'Alice: we ship Friday.'"
    payload = CreateMeetingIn(
        title=title or f"Meeting via Telegram ({datetime.now(UTC).date()})",
        participants=[],
        meeting_date=datetime.now(UTC),
        transcript=[TranscriptSegmentIn(**s) for s in segments],
    )
    meeting = await meetings_svc.create_meeting(db, user.id, payload)
    try:
        result = await analyze(db, user.id, meeting.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram_analyze_failed", error=str(exc))
        return (
            f"Created '{meeting.title}' with {len(segments)} segments, "
            "but analysis failed. Try Analyze again from the app."
        )

    lines = [f"Logged and analyzed '{meeting.title}' ({len(segments)} segments)."]
    if result.summary:
        lines.append("\nSummary:")
        lines += [f"- {i.text}" for i in result.summary[:3]]
    if result.action_items:
        lines.append("\nAction items:")
        for a in result.action_items[:5]:
            who = f" ({a.assignee})" if a.assignee else ""
            lines.append(f"- {a.task}{who}")
    lines.append(f"\nGrounding score: {round(result.grounding_score * 100)}%. View it in the app.")
    return "\n".join(lines)


async def _overdue_text(db: AsyncSession, user_id: str) -> str:
    now = datetime.now(UTC)
    items = (
        (
            await db.execute(
                select(ActionItem)
                .join(Meeting, Meeting.id == ActionItem.meeting_id)
                .where(
                    Meeting.user_id == user_id,
                    ActionItem.status != ActionItemStatus.COMPLETED,
                    ActionItem.due_date < now,
                )
                .order_by(ActionItem.due_date.asc())
                .limit(15)
            )
        )
        .scalars()
        .all()
    )
    if not items:
        return "Nothing is overdue. Nice."
    out = [f"You have {len(items)} overdue action items:"]
    for a in items:
        who = a.assignee or "unassigned"
        out.append(f"- {a.task} ({who}, due {a.due_date.date()})")
    return "\n".join(out)


async def _meetings_text(db: AsyncSession, user_id: str) -> str:
    meetings = (
        (
            await db.execute(
                select(Meeting)
                .where(Meeting.user_id == user_id)
                .order_by(Meeting.created_at.desc())
                .limit(8)
            )
        )
        .scalars()
        .all()
    )
    if not meetings:
        return "No meetings yet. Paste a transcript or upload a file to log one."
    out = ["Recent meetings:"]
    for m in meetings:
        out.append(f"- {m.title} ({m.meeting_date.date()}, {m.status.value})")
    return "\n".join(out)


async def handle_message(db: AsyncSession, message: dict) -> None:
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return

    owner = await get_owner(db)
    if owner is None:
        await telegram_service.send_message(chat_id, "No Hintro account is configured for me yet.")
        return

    await telegram_service.send_chat_action(chat_id, "typing")

    document = message.get("document")
    text = (message.get("text") or message.get("caption") or "").strip()

    if document:
        content = await telegram_service.download_file(document["file_id"])
        if not content:
            await telegram_service.send_message(
                chat_id, "I couldn't read that file. Send a .txt, .vtt, or .srt."
            )
            return
        fname = document.get("file_name", "Transcript")
        title = fname.rsplit(".", 1)[0]
        reply = await _log_meeting(db, owner, content, title)
        await telegram_service.send_message(chat_id, reply)
        return

    if not text:
        await telegram_service.send_message(chat_id, HELP)
        return

    lower = text.lower()
    if lower.startswith("/start"):
        await telegram_service.send_message(chat_id, f"Hi {owner.name.split()[0]}! {HELP}")
    elif lower.startswith("/help"):
        await telegram_service.send_message(chat_id, HELP)
    elif lower.startswith("/overdue"):
        await telegram_service.send_message(chat_id, await _overdue_text(db, owner.id))
    elif lower.startswith("/meetings"):
        await telegram_service.send_message(chat_id, await _meetings_text(db, owner.id))
    elif lower.startswith("/log"):
        await telegram_service.send_message(
            chat_id, await _log_meeting(db, owner, text[4:].strip(), None)
        )
    elif _looks_like_transcript(text):
        await telegram_service.send_message(chat_id, await _log_meeting(db, owner, text, None))
    else:
        context = await _build_context(db, owner.id)
        await telegram_service.send_message(chat_id, await _groq_reply(text, context))
