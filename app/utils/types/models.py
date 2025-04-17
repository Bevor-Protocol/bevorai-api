from datetime import datetime
from typing import Optional, TypeVar

from pydantic import BaseModel, Field

from app.utils.types.common import ModelId, NullableModelId
from app.utils.types.enums import (
    AppTypeEnum,
    AuditStatusEnum,
    AuditTypeEnum,
    ClientTypeEnum,
    ContractMethodEnum,
    FindingLevelEnum,
    NetworkEnum,
    TransactionTypeEnum,
)
from app.utils.types.mixins import CreatedAtMixin, FkMixin, IdMixin

"""
Models directly are not serializable. Rely on pydantic for response types.

These also largely help inferring openapi specs + schema.
"""

T = TypeVar("T", bound="BaseModel")


class BaseSchema(BaseModel, IdMixin, CreatedAtMixin):
    id: ModelId
    created_at: datetime
    """Base schema with common serialization methods"""

    class Config:
        from_attributes = True


class AppSchema(BaseSchema, FkMixin):
    owner_id: NullableModelId = None
    name: str
    type: AppTypeEnum


class AuditSchema(BaseSchema):
    status: AuditStatusEnum = Field(description="enumerated status of the audit")
    audit_type: AuditTypeEnum = Field(description="enumerated type of audit")
    processing_time_seconds: Optional[int] = Field(
        default=None, description="total processing time, if applicable"
    )


class UserSchema(BaseSchema):
    address: str = Field(description="wallet address of user")


class PermissionSchema(BaseSchema, FkMixin):
    client_type: ClientTypeEnum
    user_id: NullableModelId = None
    app_id: NullableModelId = None
    can_create_app: bool
    can_create_api_key: bool


class PromptSchema(BaseSchema):
    audit_type: str
    tag: str
    version: str
    content: str
    is_active: bool


class TransactionSchema(BaseSchema, FkMixin):
    app_id: NullableModelId = None
    user_id: NullableModelId = None
    type: TransactionTypeEnum
    amount: float


class ContractSchema(BaseSchema):
    method: ContractMethodEnum = Field(
        description="method used to upload contract code"
    )
    address: Optional[str] = Field(
        default=None, description="contract address, if applicable"
    )
    network: Optional[NetworkEnum] = Field(
        default=None, description="network that the contract is on, if applicable"
    )
    is_available: bool = Field(description="whether source code is available")
    code: Optional[str] = Field(default=None)


class IntermediateResponsePartialSchema(BaseSchema):
    step: str
    status: AuditStatusEnum


class IntermediateResponseSchema(IntermediateResponsePartialSchema, FkMixin):
    audit_id: NullableModelId = None
    prompt_id: NullableModelId = None
    processing_time_seconds: Optional[int] = None
    result: Optional[str] = None


class FindingSchema(BaseSchema):
    level: FindingLevelEnum
    name: Optional[str] = None
    explanation: Optional[str] = None
    recommendation: Optional[str] = None
    reference: Optional[str] = None
    is_attested: bool = False
    is_verified: bool = False
    feedback: Optional[str] = None
