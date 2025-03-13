from typing import Optional
from uuid import UUID

from pydantic import field_serializer

from app.utils.types.enums import AppTypeEnum

from .shared import IdResponse


class AppPydantic(IdResponse):
    owner_id: Optional[str | UUID] = None
    name: str
    type: AppTypeEnum

    @field_serializer("owner_id")
    def convert_owner_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id
