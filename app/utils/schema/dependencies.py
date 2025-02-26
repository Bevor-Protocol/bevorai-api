from uuid import UUID

from pydantic import BaseModel, field_serializer

from app.utils.types.enums import AuthScopeEnum, ClientTypeEnum


class AuthState(BaseModel):
    user_id: str | UUID | None = None
    app_id: str | UUID | None = None
    credit_consumer_id: str | UUID | None = None
    is_delegator: bool = False
    scope: AuthScopeEnum
    client_type: ClientTypeEnum

    @field_serializer("user_id", "app_id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id
