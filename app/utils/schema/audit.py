from typing import Optional

from pydantic import BaseModel, Field

from app.utils.types.enums import AuditStatusEnum, AuditTypeEnum, FindingLevelEnum

from .shared import CreatedAtResponse, IdResponse


class FindingPydantic(IdResponse):
    level: FindingLevelEnum = Field(description="severity level")
    name: Optional[str] = Field(default=None, description="plain text name of finding")
    explanation: Optional[str] = Field(
        default=None, description="plain text explanation of finding"
    )
    recommendation: Optional[str] = Field(
        default=None, description="plain text recommendation for resolving finding"
    )
    reference: Optional[str] = Field(
        default=None, description="code reference for finding"
    )
    is_attested: bool = Field(
        description="whether the caller had attested to the finding"
    )
    is_verified: bool = Field(description="whether the caller verified finding")
    feedback: Optional[str] = Field(
        default=None, description="feedback for the finding, if any"
    )


class AuditPydantic(IdResponse, CreatedAtResponse):
    status: AuditStatusEnum = Field(description="enumerated status of the audit")
    version: str = Field(description="internal version used to create the audit")
    audit_type: AuditTypeEnum = Field(description="enumerated type of audit")
    processing_time_seconds: Optional[int] = Field(
        default=None, description="total processing time, if applicable"
    )
    result: Optional[str] = Field(default=None, description="audit result in markdown")


class AuditStepPydantic(BaseModel):
    step: str = Field(description="name of intermediate step used in creating an audit")
    status: AuditStatusEnum = Field(description="status of the intermediate step")
    processing_time_seconds: Optional[int] = Field(
        description="total processing time, if applicable"
    )
