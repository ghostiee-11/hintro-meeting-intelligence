from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.redis import cache
from app.db.session import SessionLocal
from app.schemas.misc import EvaluationOut, HealthOut

router = APIRouter(tags=["system"])

FEATURES = [
    "JWT Authentication",
    "Meeting Management (pagination + filtering)",
    "AI Meeting Analysis (Gemini with Groq fallback)",
    "Grounded citations with deterministic verification",
    "Hallucination prevention and grounding scores",
    "Action item management and status tracking",
    "Overdue detection",
    "Scheduled reminder job (GitHub Actions cron)",
    "Telegram two-way reminders + Discord reminders",
    "Semantic search (pgvector)",
    "Analytics dashboard",
    "Unified response format + trace IDs",
    "Structured logging",
    "Global error handling and validation",
    "Redis caching and rate limiting",
    "Docker, CI/CD, unit and integration tests",
]


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    """Raw health contract: { status: "UP", checks: {...} }. Excluded from envelope."""
    db_status = "down"
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        db_status = "down"
    redis_status = "up" if await cache.ping() else "disabled"
    return HealthOut(status="UP", checks={"database": db_status, "redis": redis_status})


@router.get("/api/evaluation", response_model=EvaluationOut)
async def evaluation() -> EvaluationOut:
    """Candidate metadata. Excluded from the response envelope to match the contract."""
    return EvaluationOut(
        candidate_name=settings.candidate_name,
        email=settings.candidate_email,
        repository_url=settings.repository_url,
        deployed_url=settings.deployed_url,
        external_integration="Telegram Bot API + Discord Webhook",
        features=FEATURES,
    )
