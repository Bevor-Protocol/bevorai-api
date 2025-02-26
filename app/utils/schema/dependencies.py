from uuid import UUID

from pydantic import BaseModel, field_serializer

from app.utils.types.enums import RoleEnum


class AuthState(BaseModel):
    user_id: str | UUID | None = None
    app_id: str | UUID | None = None
    consumes_credits: bool
    credit_consumer_user_id: str | UUID | None = None
    is_delegated: bool = False
    role: RoleEnum

    @field_serializer("user_id", "app_id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id
