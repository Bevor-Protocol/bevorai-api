from typing import Optional

from pydantic import BaseModel, Field

from app.utils.types.enums import AuditStatusEnum, AuditTypeEnum, FindingLevelEnum

from .audit import AuditPydantic, AuditStepPydantic, FindingPydantic
from .contract import ContractPydantic, ContractWithCodePydantic
from .shared import CreatedAtResponse, IdResponse, Timeseries
from .user import UserPydantic


class GetAuditStatusResponse(BaseModel):
    status: AuditStatusEnum = Field(
        description="status of entire audit, depends on steps"
    )
    steps: list[AuditStepPydantic] = Field(default_factory=lambda: [])


class GetCostEstimateResponse(BaseModel):
    credits: int


class CreateEvalResponse(IdResponse):
    status: AuditStatusEnum = Field(description="initial status of created audit")


class UploadContractResponse(BaseModel):
    exists: bool = Field(
        description="whether at least 1 contract was found with source code"
    )
    exact_match: bool = Field(
        description="whether there is only 1 candidate contract with source code available"  # noqa
    )
    contract: Optional[ContractWithCodePydantic] = Field(
        default=None, description="contract information, if available"
    )


class AuditMetadata(IdResponse, CreatedAtResponse):
    n: int
    audit_type: AuditTypeEnum
    status: AuditStatusEnum
    contract: ContractPydantic
    user: UserPydantic


class AuditResponse(AuditPydantic):
    findings: list[FindingPydantic] = Field(default_factory=lambda: [])
    contract: ContractWithCodePydantic
    user: UserPydantic


class AuditsResponse(BaseModel):
    results: list[AuditMetadata] = Field(
        default_factory=lambda: [], description="array of audits"
    )
    more: bool = Field(
        description="whether more audits exist, given page and page_size"
    )
    total_pages: int = Field(description="total pages, given page_size")


class AuthInfo(BaseModel):
    exists: bool
    is_active: bool
    can_create: bool


class UserAppInfo(BaseModel):
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
    app: UserAppInfo
    n_contracts: int
    n_audits: int


class AppInfoResponse(IdResponse, CreatedAtResponse):
    name: str
    n_audits: int
    n_contracts: int


class AllStatsResponse(BaseModel):
    n_audits: int
    n_contracts: int
    n_users: int
    n_apps: int
    findings: dict[AuditTypeEnum, dict[FindingLevelEnum, int]]
    audits_timeseries: list[Timeseries]
    users_timeseries: list[Timeseries]


class StaticAnalysisTokenResult(BaseModel):
    is_mintable: bool = Field(
        description="Whether the token contract has minting capabilities"
    )
    is_honeypot: bool = Field(
        description="Whether the token contract exhibits honeypot characteristics"
    )
    can_steal_fees: bool = Field(
        description="Whether the token contract has functions that could be used to steal fees"  # noqa
    )
    can_self_destruct: bool = Field(
        description="Whether the token contract contains self-destruct functionality"
    )
    has_proxy_functions: bool = Field(
        description="Whether the token contract contains proxy/delegation functions"
    )
    has_allowlist: bool = Field(
        description="Whether the token contract implements allowlist functionality"
    )
    has_blocklist: bool = Field(
        description="Whether the token contract implements blocklist functionality"
    )
    can_terminate_transactions: bool = Field(
        description="Whether the token contract can terminate transactions"
    )
