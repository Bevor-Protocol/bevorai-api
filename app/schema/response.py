from datetime import datetime, timezone
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, model_validator

from app.utils.enums import (
    AuditStatusEnum,
    AuditTypeEnum,
    ContractMethodEnum,
    NetworkEnum,
    ResponseStructureEnum,
)


class _GetEvalContract(BaseModel):
    code: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    network: Optional[NetworkEnum] = Field(default=None)


class _GetEvalAudit(BaseModel):
    type: ResponseStructureEnum
    result: Optional[Union[str, dict]] = Field(default=None)

    @model_validator(mode="after")
    def validate_result_type(self) -> "_GetEvalAudit":
        if not self.result:
            return self
        if self.response_type == ResponseStructureEnum.JSON:
            if not isinstance(self.result, dict):
                raise ValueError(
                    "Result must be a dictionary when response_type is JSON"
                )
        else:
            if not isinstance(self.result, str):
                raise ValueError(
                    "Result must be a string when response_type is RAW or MARKDOWN"
                )
        return self


class _GetEvalData(BaseModel):
    contract: _GetEvalContract
    audit: _GetEvalAudit


class GetEvalResponse(BaseModel):
    id: str | UUID
    status: Optional[AuditStatusEnum] = None
    exists: bool
    error: Optional[str] = None
    data: Optional[_GetEvalData] = Field(default_factory=lambda: {})

    @field_serializer("id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class GetCostEstimate(BaseModel):
    credits: int


class CreateEvalResponse(BaseModel):
    id: str | UUID
    status: AuditStatusEnum

    @field_serializer("id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class _ContractCandidateResponse(BaseModel):
    id: str | UUID
    source_code: str
    network: Optional[NetworkEnum] = None
    is_available: bool

    @field_serializer("id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class UploadContractResponse(BaseModel):
    exists: bool
    exact_match: bool
    candidates: list[_ContractCandidateResponse] = Field(default_factory=lambda: [])


class WebhookResponseData(BaseModel):
    status: AuditStatusEnum
    id: str


class WebhookResponse(BaseModel):
    success: bool
    error: Optional[str] = Field(default=None)
    result: Optional[WebhookResponseData] = Field(default=None)


class AnalyticsContract(BaseModel):
    id: Union[str, UUID]
    method: ContractMethodEnum
    address: Optional[str]
    network: Optional[NetworkEnum]

    @field_serializer("id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class AnalyticsAudit(BaseModel):
    n: int
    id: str | UUID
    created_at: datetime
    app_id: str | UUID | None = None
    user_id: Optional[str] = None
    audit_type: AuditTypeEnum
    status: AuditStatusEnum
    contract: AnalyticsContract

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.astimezone(timezone.utc).isoformat()

    @field_serializer("id", "app_id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class AnalyticsResponse(BaseModel):
    results: list[AnalyticsAudit]
    more: bool
    total_pages: int


class StatsResponse(BaseModel):
    n_audits: int
    n_contracts: int
    n_users: int
    n_apps: int
    findings: dict


class UserInfo(BaseModel):
    id: Union[str, UUID]
    address: str
    created_at: datetime
    total_credits: float
    remaining_credits: float

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.astimezone(timezone.utc).isoformat()

    @field_serializer("id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class AuthInfo(BaseModel):
    exists: bool
    is_active: bool
    can_create: bool


class AppInfo(BaseModel):
    exists: bool
    name: Optional[str] = None
    can_create: bool
    can_create_auth: Optional[bool] = False
    exists_auth: Optional[bool] = False


class UserInfoResponse(BaseModel):
    user: UserInfo
    auth: AuthInfo
    app: AppInfo
    audits: list[AnalyticsAudit]
    n_contracts: int
    n_audits: int
