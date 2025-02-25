from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, field_serializer


class IdResponse(BaseModel):
    id: str | UUID

    @field_serializer("id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class CreatedAtResponse(BaseModel):
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime):
        return dt.astimezone(timezone.utc).isoformat()


class Timeseries(BaseModel):
    date: str
    count: int


class BooleanResponse(BaseModel):
    success: bool


class ErrorResponse(BaseModel):
    detail: str
