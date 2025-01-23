from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, field_serializer, model_validator

from app.utils.enums import (
    AuditStatusEnum,
    AuditTypeEnum,
    ContractMethodEnum,
    NetworkEnum,
    ResponseStructureEnum,
)


class EvalResponseData(BaseModel):
    id: str
    status: AuditStatusEnum
    contract_code: Optional[str] = Field(default=None)
    contract_address: Optional[str] = Field(default=None)
    contract_network: Optional[NetworkEnum] = Field(default=None)
    response_type: ResponseStructureEnum
    result: Optional[Union[str, dict]] = Field(default=None)

    @model_validator(mode="after")
    def validate_result_type(self) -> "EvalResponseData":
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


class EvalResponse(BaseModel):
    success: bool
    exists: bool
    error: Optional[str] = Field(default=None)
    result: Optional[EvalResponseData] = Field(default=None)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        return super().model_dump(exclude_none=True)


class WebhookResponseData(BaseModel):
    status: AuditStatusEnum
    id: str


class WebhookResponse(BaseModel):
    success: bool
    error: Optional[str] = Field(default=None)
    result: Optional[WebhookResponseData] = Field(default=None)


class AnalyticsContract(BaseModel):
    method: ContractMethodEnum
    address: Optional[str]
    network: Optional[NetworkEnum]


class AnalyticsAudit(BaseModel):
    n: int
    id: str
    created_at: datetime
    app_id: Optional[str]
    user_id: Optional[str]
    audit_type: AuditTypeEnum
    results_status: AuditStatusEnum
    contract: AnalyticsContract

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.astimezone(timezone.utc).isoformat()


class AnalyticsResponse(BaseModel):
    results: list[AnalyticsAudit]
    more: bool


class StatsResponse(BaseModel):
    n_audits: int
    n_auths: int
    n_contracts: int
    n_users: int
    n_apps: int
    findings: dict
