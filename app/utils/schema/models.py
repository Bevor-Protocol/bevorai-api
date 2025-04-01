from typing import Optional
from uuid import UUID

from pydantic import Field, field_serializer

from app.utils.schema.shared import CreatedAtResponse, IdResponse
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

"""
Models directly are not serializable. Rely on pydantic for response types.

These also largely help inferring openapi specs + schema.
"""


class BaseInstance(IdResponse, CreatedAtResponse):
    @classmethod
    def from_tortoise(cls, instance):
        return cls(**instance.__dict__)


class AppSchema(BaseInstance):
    owner_id: Optional[str | UUID] = None
    name: str
    type: AppTypeEnum

    @field_serializer("owner_id")
    def convert_owner_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class AuditSchema(BaseInstance):
    status: AuditStatusEnum = Field(description="enumerated status of the audit")
    audit_type: AuditTypeEnum = Field(description="enumerated type of audit")
    processing_time_seconds: Optional[int] = Field(
        default=None, description="total processing time, if applicable"
    )
    result: Optional[str] = Field(default=None, description="audit result in markdown")


class UserSchema(BaseInstance):
    address: str = Field(description="wallet address of user")


class PermissionSchema(BaseInstance):
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


class PromptSchema(BaseInstance):
    audit_type: str
    tag: str
    version: str
    content: str
    is_active: bool


class TransactionSchema(BaseInstance):
    app_id: Optional[str | UUID] = None
    user_id: Optional[str | UUID] = None
    type: TransactionTypeEnum
    amount: float

    @field_serializer("user_id", "app_id")
    def convert_owner_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class ContractSchema(BaseInstance):
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
    code: Optional[str] = Field(default=None, alias="raw_code")


class IntermediateResponseSchema(BaseInstance):
    audit_id: Optional[str | UUID] = None
    prompt_id: Optional[str | UUID] = None
    step: str
    status: AuditStatusEnum
    processing_time_seconds: Optional[int] = None
    result: Optional[str] = None

    @field_serializer("audit_id", "prompt_id")
    def convert_owner_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class FindingSchema(BaseInstance):
    level: FindingLevelEnum
    name: Optional[str] = None
    explanation: Optional[str] = None
    recommendation: Optional[str] = None
    reference: Optional[str] = None
    is_attested: bool = False
    is_verified: bool = False
    feedback: Optional[str] = None
