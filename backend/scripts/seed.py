"""Seed the database with a demo user and a set of realistic meetings.

Creates ~8 meetings with natural transcripts, runs the real grounding analysis on
each (when an LLM key is configured), and varies action-item statuses and due dates
so the dashboard, Kanban board, overdue view, and semantic search are populated.

Run with: uv run python -m scripts.seed
Demo login: demo@hintro.ai / demo-password-123
"""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import ActionItem, ActionItemStatus, Meeting, TranscriptSegment, User
from app.services.analysis import analyze
from app.services.llm.service import llm_service

# Each transcript is a list of (speaker, text); timestamps are assigned sequentially.
MEETINGS = [
    {
        "title": "Sprint Planning",
        "days_ago": 2,
        "participants": ["alice@example.com", "bob@example.com", "john@example.com"],
        "lines": [
            ("John", "We should launch next Friday."),
            ("Alice", "I will prepare the release notes by Wednesday."),
            ("Bob", "We decided to use PostgreSQL for the new service."),
            ("Alice", "Let us follow up on the marketing plan next week."),
            ("John", "Bob will set up the staging environment before the launch."),
        ],
    },
    {
        "title": "Daily Standup - Web Team",
        "days_ago": 1,
        "participants": ["alice@example.com", "carol@example.com", "dan@example.com"],
        "lines": [
            ("Carol", "Yesterday I finished the login page and started on the dashboard."),
            ("Dan", "I am blocked on the API contract for the analytics endpoint."),
            ("Alice", "I will share the analytics API contract with Dan by end of day."),
            ("Carol", "We agreed to drop the carousel from the homepage for now."),
            ("Dan", "I will pick up the search bar once the contract is ready."),
        ],
    },
    {
        "title": "Q3 Product Roadmap Review",
        "days_ago": 5,
        "participants": ["priya@example.com", "john@example.com", "alice@example.com"],
        "lines": [
            ("Priya", "Our top priority for Q3 is the reminders integration."),
            ("John", "We decided to prioritize Telegram before Slack."),
            ("Alice", "I will draft the integration spec by next Monday."),
            ("Priya", "Let us revisit pricing after the launch."),
            ("John", "Priya will present the roadmap to leadership on the 20th."),
        ],
    },
    {
        "title": "Incident Retro: API Outage",
        "days_ago": 7,
        "participants": ["bob@example.com", "dan@example.com", "sara@example.com"],
        "lines": [
            ("Sara", "The outage was caused by a missing database index on the meetings table."),
            ("Bob", "We decided to add automated alerts for slow queries."),
            ("Dan", "I will add the missing index and a migration this week."),
            ("Sara", "Bob will write a postmortem document by Thursday."),
            ("Dan", "We should add a load test to the CI pipeline as a follow-up."),
        ],
    },
    {
        "title": "Design Review: Onboarding Flow",
        "days_ago": 9,
        "participants": ["carol@example.com", "priya@example.com", "alice@example.com"],
        "lines": [
            ("Carol", "The new onboarding has three steps instead of five."),
            ("Priya", "We agreed to remove the credit card requirement during signup."),
            ("Carol", "I will update the Figma prototype by Friday."),
            ("Alice", "Let us A/B test the new flow against the old one."),
            ("Priya", "Carol will hand off the final designs to engineering next week."),
        ],
    },
    {
        "title": "Customer Discovery: Acme Corp",
        "days_ago": 11,
        "participants": ["john@example.com", "sara@example.com"],
        "lines": [
            ("Sara", "Acme wants exportable meeting summaries for their compliance team."),
            ("John", "They confirmed they would pilot the product in October."),
            ("Sara", "I will send Acme a follow-up proposal by Wednesday."),
            ("John", "We decided to add a CSV export feature to the backlog."),
            ("Sara", "John will schedule a technical deep dive with their engineers."),
        ],
    },
    {
        "title": "Marketing Sync: Launch Campaign",
        "days_ago": 13,
        "participants": ["priya@example.com", "dan@example.com", "alice@example.com"],
        "lines": [
            ("Priya", "The launch campaign goes live on the first of next month."),
            ("Alice", "I will write the launch blog post by the 25th."),
            ("Dan", "We decided to focus the campaign on the grounded-citations feature."),
            ("Priya", "Dan will prepare three social media graphics."),
            ("Alice", "Let us follow up with the design team about the demo video."),
        ],
    },
    {
        "title": "Engineering 1:1",
        "days_ago": 15,
        "participants": ["bob@example.com", "carol@example.com"],
        "lines": [
            ("Bob", "You did great work on the authentication module."),
            ("Carol", "I would like to take ownership of the search feature."),
            ("Bob", "We agreed that Carol will lead the semantic search work."),
            ("Carol", "I will put together a short design doc by next week."),
            ("Bob", "Let us revisit your growth goals at the next review."),
        ],
    },
]


def to_segments(lines: list[tuple[str, str]]) -> list[TranscriptSegment]:
    segments = []
    for ordinal, (speaker, text) in enumerate(lines):
        total = ordinal * 30
        ts = f"{total // 60:02d}:{total % 60:02d}"
        segments.append(
            TranscriptSegment(ordinal=ordinal, timestamp=ts, speaker=speaker, text=text)
        )
    return segments


async def vary_action_items(db, user_id: str) -> None:
    """Spread statuses and due dates so the board and overdue view look realistic."""
    items = (
        (
            await db.execute(
                select(ActionItem)
                .join(Meeting, Meeting.id == ActionItem.meeting_id)
                .where(Meeting.user_id == user_id)
                .order_by(ActionItem.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    now = datetime.now(UTC)
    # Cycle: overdue+pending, future+pending, in-progress, completed.
    for i, item in enumerate(items):
        bucket = i % 4
        if bucket == 0:
            item.due_date = now - timedelta(days=2 + (i % 3))  # overdue
            item.status = ActionItemStatus.PENDING
        elif bucket == 1:
            item.due_date = now + timedelta(days=3 + (i % 4))  # upcoming
            item.status = ActionItemStatus.PENDING
        elif bucket == 2:
            item.due_date = now + timedelta(days=1)
            item.status = ActionItemStatus.IN_PROGRESS
        else:
            item.due_date = now - timedelta(days=1)
            item.status = ActionItemStatus.COMPLETED
    await db.commit()


async def seed() -> None:
    async with SessionLocal() as db:
        email = "demo@hintro.ai"
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            user = User(
                email=email, name="Demo User", password_hash=hash_password("demo-password-123")
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        existing = (
            (await db.execute(select(Meeting).where(Meeting.user_id == user.id))).scalars().all()
        )
        existing_titles = {m.title for m in existing}

        created_ids: list[str] = []
        for spec in MEETINGS:
            if spec["title"] in existing_titles:
                continue
            meeting = Meeting(
                user_id=user.id,
                title=spec["title"],
                meeting_date=datetime.now(UTC) - timedelta(days=spec["days_ago"]),
                participants=spec["participants"],
            )
            meeting.segments = to_segments(spec["lines"])
            db.add(meeting)
            await db.commit()
            await db.refresh(meeting)
            created_ids.append(meeting.id)

        print(f"Created {len(created_ids)} new meetings.")

        if llm_service.has_provider():
            for i, mid in enumerate(created_ids, 1):
                try:
                    await analyze(db, user.id, mid)
                    print(f"  Analyzed meeting {i}/{len(created_ids)}")
                except Exception as exc:  # noqa: BLE001
                    print(f"  Analysis failed for {mid}: {exc}")
            await vary_action_items(db, user.id)
            print("Varied action item statuses and due dates.")
        else:
            print("No LLM key configured; meetings created without analysis.")

        print("Seed complete. Demo login: demo@hintro.ai / demo-password-123")


if __name__ == "__main__":
    asyncio.run(seed())
