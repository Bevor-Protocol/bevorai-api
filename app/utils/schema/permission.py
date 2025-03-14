from typing import Optional
from uuid import UUID

from pydantic import field_serializer

from app.utils.types.enums import ClientTypeEnum

from .shared import IdResponse


class PermissionPydantic(IdResponse):
    client_type: ClientTypeEnum
    user_id: Optional[str | UUID] = None
    app_id: Optional[str | UUID] = None
    can_create_app: bool
    can_create_api_key: bool

    @field_serializer("user_id", "app_id")
    def convert_owner_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id
