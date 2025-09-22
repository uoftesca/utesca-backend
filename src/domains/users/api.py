"""
User domain API endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_users():
    """Get all users."""
    return {"message": "Users endpoint - to be implemented"}


@router.get("/{user_id}")
async def get_user(user_id: int):
    """Get user by ID."""
    return {"message": f"User {user_id} endpoint - to be implemented"}
