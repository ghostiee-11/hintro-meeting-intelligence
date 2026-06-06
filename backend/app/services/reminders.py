from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import get_trace_id
from app.core.logging import get_logger
from app.models import (
    ActionItem,
    ActionItemStatus,
    Meeting,
    ReminderChannel,
    ReminderLog,
    ReminderStatus,
)
from app.schemas.misc import ReminderDetail, ReminderRunResult
from app.services.integrations.discord import discord_service
from app.services.integrations.telegram import ReminderTarget, telegram_service

logger = get_logger("reminders")

DEDUPE_WINDOW_HOURS = 24


async def run_reminders(db: AsyncSession) -> ReminderRunResult:
    """The scheduled reminder workflow, triggered by the GitHub Actions cron.

    1. Identifies overdue action items (not completed, due date in the past).
    2. Triggers reminder notifications through the configured integrations.
    3. Records reminder history and dedupes so an item is not reminded more than
       once per DEDUPE_WINDOW_HOURS even if the cron double-fires.
    """
    trace_id = get_trace_id()
    now = datetime.now(UTC)

    overdue = (
        (
            await db.execute(
                select(ActionItem)
                .where(ActionItem.status != ActionItemStatus.COMPLETED, ActionItem.due_date < now)
                .order_by(ActionItem.due_date.asc())
            )
        )
        .scalars()
        .all()
    )

    channels = []
    if telegram_service.is_configured():
        channels.append((ReminderChannel.TELEGRAM, telegram_service.send_reminder))
    if discord_service.is_configured():
        channels.append((ReminderChannel.DISCORD, discord_service.send_reminder))

    result = ReminderRunResult(
        overdue_count=len(overdue),
        reminders_sent=0,
        skipped=0,
        failed=0,
        channels=[c.value for c, _ in channels],
        details=[],
    )

    cutoff = now - timedelta(hours=DEDUPE_WINDOW_HOURS)

    for item in overdue:
        target = ReminderTarget(
            id=item.id, task=item.task, assignee=item.assignee, due_date=item.due_date
        )
        for channel, send in channels:
            recent = (
                await db.execute(
                    select(ReminderLog).where(
                        ReminderLog.action_item_id == item.id,
                        ReminderLog.channel == channel,
                        ReminderLog.status == ReminderStatus.SENT,
                        ReminderLog.sent_at >= cutoff,
                    )
                )
            ).scalar_one_or_none()
            if recent is not None:
                result.skipped += 1
                result.details.append(
                    ReminderDetail(action_item_id=item.id, channel=channel.value, status="SKIPPED")
                )
                continue

            send_result = await send(target)
            status = ReminderStatus.SENT if send_result.ok else ReminderStatus.FAILED
            db.add(
                ReminderLog(
                    action_item_id=item.id,
                    channel=channel,
                    status=status,
                    payload=send_result.payload,
                    error=send_result.error,
                    trace_id=trace_id,
                )
            )
            if send_result.ok:
                result.reminders_sent += 1
                result.details.append(
                    ReminderDetail(action_item_id=item.id, channel=channel.value, status="SENT")
                )
            else:
                result.failed += 1
                result.details.append(
                    ReminderDetail(
                        action_item_id=item.id,
                        channel=channel.value,
                        status="FAILED",
                        error=send_result.error,
                    )
                )

    await db.commit()
    logger.info(
        "reminder_run",
        overdue=result.overdue_count,
        sent=result.reminders_sent,
        skipped=result.skipped,
        failed=result.failed,
    )
    return result


async def reminder_history(db: AsyncSession, user_id: str, limit: int = 50) -> list[dict]:
    rows = (
        (
            await db.execute(
                select(ReminderLog)
                .join(ActionItem, ActionItem.id == ReminderLog.action_item_id)
                .join(Meeting, Meeting.id == ActionItem.meeting_id)
                .where(Meeting.user_id == user_id)
                .order_by(ReminderLog.sent_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "actionItemId": r.action_item_id,
            "channel": r.channel.value,
            "status": r.status.value,
            "error": r.error,
            "sentAt": r.sent_at.isoformat(),
        }
        for r in rows
    ]


async def handle_telegram_callback(db: AsyncSession, data: str) -> str:
    """Processes a Telegram inline-button callback: status:<id>:<STATUS>."""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "status":
        return "Unrecognized action"
    _, item_id, status_str = parts
    valid = {s.value for s in ActionItemStatus}
    if status_str not in valid:
        return "Unrecognized status"
    item = await db.get(ActionItem, item_id)
    if item is None:
        return "Action item no longer exists"
    item.status = ActionItemStatus(status_str)
    await db.commit()
    return f"Marked {status_str.replace('_', ' ').lower()}"
