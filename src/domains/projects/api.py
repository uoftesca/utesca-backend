"""
Project domain API endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_projects():
    """Get all projects."""
    return {"message": "Projects endpoint - to be implemented"}


@router.get("/{project_id}")
async def get_project(project_id: int):
    """Get project by ID."""
    return {"message": f"Project {project_id} endpoint - to be implemented"}
