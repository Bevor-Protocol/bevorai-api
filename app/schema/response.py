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


class IdResponse(BaseModel):
    id: str | UUID

    @field_serializer("id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class CreatedAtResponse(BaseModel):
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.astimezone(timezone.utc).isoformat()


class _Finding(BaseModel):
    id: str
    level: str
    name: Optional[str] = None
    explanation: Optional[str] = None
    recommendation: Optional[str] = None
    reference: Optional[str] = None
    is_attested: bool
    is_verified: bool
    feedback: Optional[str] = None


class _Contract(BaseModel):
    address: Optional[str] = None
    network: Optional[NetworkEnum] = None
    code: Optional[str] = None


class _User(BaseModel):
    id: str
    address: str


class GetAuditResponse(BaseModel):
    status: str
    version: str
    audit_type: AuditTypeEnum
    processing_time_seconds: Optional[int]
    result: Optional[str] = None
    findings: list[_Finding]
    contract: _Contract
    user: _User


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
        if self.type == ResponseStructureEnum.JSON:
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


class GetEvalResponse(IdResponse):
    status: Optional[AuditStatusEnum] = None
    exists: bool
    error: Optional[str] = None
    data: Optional[_GetEvalData] = Field(default_factory=lambda: {})


class _GetAuditStep(BaseModel):
    step: str
    status: AuditStatusEnum


class GetAuditStatusResponse(BaseModel):
    status: AuditStatusEnum
    steps: list[_GetAuditStep] = Field(default_factory=lambda: [])


class GetCostEstimateResponse(BaseModel):
    credits: int


class CreateEvalResponse(IdResponse):
    status: AuditStatusEnum


class _ContractCandidateResponse(IdResponse):
    source_code: str
    network: Optional[NetworkEnum] = None
    is_available: bool


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


class AnalyticsContract(IdResponse):
    method: ContractMethodEnum
    address: Optional[str]
    network: Optional[NetworkEnum]


class AnalyticsAudit(IdResponse, CreatedAtResponse):
    n: int
    app_id: Optional[str | UUID] = None
    user_id: Optional[str | UUID] = None
    audit_type: AuditTypeEnum
    status: AuditStatusEnum
    contract: AnalyticsContract

    @field_serializer("app_id", "user_id")
    def convert_to_string(self, id):
        if not id:
            return id
        if isinstance(id, UUID):
            return str(id)
        return id


class AnalyticsResponse(BaseModel):
    results: list[AnalyticsAudit]
    more: bool
    total_pages: int


class Timeseries(BaseModel):
    date: str
    count: int


class StatsResponse(BaseModel):
    n_audits: int
    n_contracts: int
    n_users: int
    n_apps: int
    findings: dict
    audits_timeseries: list[Timeseries]
    users_timeseries: list[Timeseries]


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


class UserInfoResponse(IdResponse, CreatedAtResponse):
    address: str
    total_credits: float
    remaining_credits: float
    auth: AuthInfo
    app: AppInfo
    n_contracts: int
    n_audits: int


class BooleanResponse(BaseModel):
    success: bool


class GetContractResponse(BaseModel):
    method: ContractMethodEnum
    is_available: bool
    address: Optional[str] = None
    network: Optional[NetworkEnum] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
