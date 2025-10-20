"""
Main API v1 router that includes all domain routers.

This router aggregates all domain-specific routers and exposes them
under the /api/v1 prefix.

Domain routers to be added:
- /auth - Authentication and profile management
- /events - Event creation, approval, and management
- /users - User and team member management
- /departments - Department management
- /announcements - Club-wide announcements
- /applications - Application tracking and management
- /analytics - Event and registration analytics
- /public - Public-facing endpoints (for utesca.ca)
"""

from fastapi import APIRouter

# Domain router imports
from domains.auth.api import router as auth_router
from domains.departments.api import router as departments_router
from domains.users.api import router as users_router

# Create main API router
api_router = APIRouter()

# Include domain routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(departments_router, prefix="/departments", tags=["Departments"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])


# Placeholder endpoint - remove once domain routers are added
@api_router.get("/status")
async def api_status():
    """
    API v1 status endpoint.

    Returns the status of the API v1 and available endpoints.
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "message": "UTESCA Portal API v1 - Domain routers will be added here"
    }
