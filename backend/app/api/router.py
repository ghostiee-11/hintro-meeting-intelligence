from fastapi import APIRouter

from app.api.routes import (
    action_items,
    analysis,
    analytics,
    auth,
    integrations,
    meetings,
    reminders,
    search,
    system,
)

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(meetings.router)
api_router.include_router(analysis.router)
api_router.include_router(action_items.router)
api_router.include_router(reminders.router)
api_router.include_router(integrations.router)
api_router.include_router(search.router)
api_router.include_router(analytics.router)
