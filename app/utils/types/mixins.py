from datetime import datetime, timezone
from uuid import UUID

from pydantic import field_serializer

from app.utils.types.common import ModelId, NullableModelId


class IdMixin:
    @field_serializer("id")
    def convert_uuid_to_string(self, id: ModelId) -> str:
        if isinstance(id, UUID):
            return str(id)
        return id


class CreatedAtMixin:
    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime) -> str:
        return dt.astimezone(timezone.utc).isoformat()


class FkMixin:
    @field_serializer(
        "user_id",
        "app_id",
        "audit_id",
        "prompt_id",
        "contract_id",
        "owner_id",
        check_fields=False,
    )
    def convert_optional_uuid_to_string(self, id: NullableModelId) -> str | None:
        if isinstance(id, UUID):
            return str(id)
        return id
