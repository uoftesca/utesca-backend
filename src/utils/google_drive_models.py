"""
Google Drive utility models - Data models for Google Drive operations.

This module defines Pydantic models for Google Drive direct link generation.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GoogleDriveDirectLinkResponse(BaseModel):
    """Response model for Google Drive direct link generation."""

    original_url: str = Field(..., description="The original Google Drive URL provided")
    direct_url: Optional[str] = Field(None, description="The generated direct download link")
    error: Optional[str] = Field(None, description="Error message if link generation failed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "original_url": "https://drive.google.com/file/d/1GgjItC8Ly5fbWXsbe8fKaC0irR-KE6S_/view?usp=sharing",
                "direct_url": "https://drive.google.com/uc?export=download&id=1GgjItC8Ly5fbWXsbe8fKaC0irR-KE6S_",
                "error": None,
            }
        }
    )
