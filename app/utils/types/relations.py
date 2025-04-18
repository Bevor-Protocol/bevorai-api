from typing import Optional

from pydantic import Field

from app.utils.types.models import (
    AppSchema,
    AuditSchema,
    ChatSchema,
    ContractSchema,
    FindingSchema,
    IntermediateResponseSchema,
    PermissionSchema,
    UserSchema,
)


class AuditWithContractRelation(AuditSchema):
    contract: ContractSchema


class AuditRelation(AuditWithContractRelation):
    user: UserSchema


class AuditWithFindingsRelation(AuditRelation):
    findings: list[FindingSchema] = Field(default_factory=lambda: [])


class AuditWithChildrenRelation(AuditWithFindingsRelation):
    intermediate_responses: list[IntermediateResponseSchema] = Field(
        default_factory=lambda: []
    )


class UserPermissionRelation(UserSchema):
    permissions: Optional[PermissionSchema]


class AppPermissionRelation(AppSchema):
    permissions: Optional[PermissionSchema]


class ChatRelation(ChatSchema):
    audit: AuditWithContractRelation
