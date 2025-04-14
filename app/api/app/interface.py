from pydantic import BaseModel

from app.utils.types.enums import AuditTypeEnum, FindingLevelEnum
from app.utils.types.models import AppSchema
from app.utils.types.shared import Timeseries

"""
Used for HTTP request validation, response Serialization, and arbitrary typing.
"""


class AppUpsertBody(BaseModel):
    name: str


class AppInfoResponse(AppSchema):
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
