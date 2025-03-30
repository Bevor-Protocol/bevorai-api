from pydantic import BaseModel

from app.utils.schema.shared import CreatedAtResponse, IdResponse, Timeseries
from app.utils.types.enums import AuditTypeEnum, FindingLevelEnum

"""
Used for HTTP request validation, response Serialization, and arbitrary typing.
"""


class AppUpsertBody(BaseModel):
    name: str


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
