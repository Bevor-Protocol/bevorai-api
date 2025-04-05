from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, model_validator

from app.utils.types.models import (
    AppSchema,
    AuditSchema,
    FindingSchema,
    IntermediateResponseSchema,
    UserSchema,
)
from app.utils.types.enums import AuditTypeEnum

"""
Used for HTTP request validation, response Serialization, and arbitrary typing.
"""


class AdminQuerySearch(BaseModel):
    identifier: Optional[str] = None


class UpdatePermissionsBody(BaseModel):
    can_create_app: bool
    can_create_api_key: bool


class UpdatePromptBody(BaseModel):
    audit_type: Optional[AuditTypeEnum] = None
    tag: Optional[str] = None
    content: Optional[str] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def check_data(self):
        if not any([self.content, self.version, self.tag, self.is_active is not None]):
            raise HTTPException(
                status_code=400, detail="At least one field must be provided for update"
            )
        return self


class CreatePromptBody(BaseModel):
    audit_type: AuditTypeEnum
    tag: str
    content: str
    version: str
    is_active: Optional[bool] = False


class AdminPermission(BaseModel):
    can_create_app: bool
    can_create_api_key: bool


class AdminUserPermission(UserSchema):
    permission: Optional[AdminPermission]


class AdminAppPermission(AppSchema):
    permission: Optional[AdminPermission]


class AuditWithChildren(AuditSchema):
    intermediate_responses: list[IntermediateResponseSchema]
    findings: list[FindingSchema]
