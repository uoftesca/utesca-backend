"""
Repository for registration file metadata.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from supabase import Client

from .models import FileMeta


class RegistrationFilesRepository:
    """Data access layer for registration_files table."""

    def __init__(self, client: Client, schema: str):
        self.client = client
        self.schema = schema

    def create_file_record(
        self,
        event_id: UUID,
        field_name: str,
        file_url: str,
        file_name: str,
        file_size: int,
        mime_type: str,
        upload_session_id: str,
    ) -> FileMeta:
        data = {
            "event_id": str(event_id),
            "field_name": field_name,
            "file_url": file_url,
            "file_name": file_name,
            "file_size": file_size,
            "mime_type": mime_type,
            "upload_session_id": upload_session_id,
        }
        result = (
            self.client.schema(self.schema)
            .table("registration_files")
            .insert(data, returning="representation")
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to create registration file record")
        return FileMeta.model_validate(result.data[0])

    def get_files_by_registration(self, registration_id: UUID) -> List[FileMeta]:
        result = (
            self.client.schema(self.schema)
            .table("registration_files")
            .select("*")
            .eq("registration_id", str(registration_id))
            .execute()
        )
        return [FileMeta.model_validate(item) for item in result.data or []]

    def get_files_by_upload_session(self, upload_session_id: str) -> List[FileMeta]:
        result = (
            self.client.schema(self.schema)
            .table("registration_files")
            .select("*")
            .eq("upload_session_id", upload_session_id)
            .execute()
        )
        return [FileMeta.model_validate(item) for item in result.data or []]

    def get_file_for_field(
        self, upload_session_id: str, field_name: str, event_id: UUID
    ) -> List[FileMeta]:
        result = (
            self.client.schema(self.schema)
            .table("registration_files")
            .select("*")
            .eq("upload_session_id", upload_session_id)
            .eq("field_name", field_name)
            .eq("event_id", str(event_id))
            .execute()
        )
        return [FileMeta.model_validate(item) for item in result.data or []]

    def link_files_to_registration(
        self, upload_session_id: str, registration_id: UUID, event_date: datetime
    ) -> int:
        deletion_date: Optional[date] = None
        if event_date:
            deletion_date = event_date.date() + timedelta(days=30)

        update_data = {
            "registration_id": str(registration_id),
            "scheduled_deletion_date": deletion_date.isoformat() if deletion_date else None,
        }
        result = (
            self.client.schema(self.schema)
            .table("registration_files")
            .update(update_data, returning="representation")
            .eq("upload_session_id", upload_session_id)
            .execute()
        )
        return len(result.data or [])

