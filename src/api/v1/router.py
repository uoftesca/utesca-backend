"""
Main API v1 router that includes all domain routers.
"""

from fastapi import APIRouter

from src.domains.events.api import router as events_router
from src.domains.users.api import router as users_router
from src.domains.projects.api import router as projects_router

# Create main API router
api_router = APIRouter()

# Include domain routers
api_router.include_router(events_router, prefix="/events", tags=["events"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
