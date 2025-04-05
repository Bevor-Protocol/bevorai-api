from datetime import datetime
from typing import Any, Optional, Type, TypeVar, get_type_hints

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

    @classmethod
    def from_tortoise(cls: Type[T], instance: Any) -> T:
        """Convert a Tortoise model instance to a Pydantic model, with relations if needed."""
        data = instance.__dict__.copy()
        type_hints = get_type_hints(cls)

        # Then process each field, looking for relations
        for field_name, field_type in type_hints.items():
            value = getattr(instance, field_name, None)

            # Handle single relationships
            if hasattr(value, "__class__") and hasattr(value, "id"):
                schema_class = field_type
                data[field_name] = schema_class.from_tortoise(value)

            # Handle lists of relationships
            elif isinstance(value, (list, set)):
                if field_name in type_hints:
                    schema_class = type_hints[field_name].__args__[0]
                    data[field_name] = [
                        schema_class.from_tortoise(item) for item in value
                    ]

        return cls.model_validate(data)


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
    result: Optional[str] = Field(default=None, description="audit result in markdown")


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
    code: Optional[str] = Field(default=None, alias="raw_code")


class IntermediateResponseSchema(BaseSchema, FkMixin):
    audit_id: NullableModelId = None
    prompt_id: NullableModelId = None
    step: str
    status: AuditStatusEnum
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
