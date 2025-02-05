from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_serializer

from app.utils.enums import (
    AppTypeEnum,
    AuditStatusEnum,
    AuditTypeEnum,
    ClientTypeEnum,
    ContractMethodEnum,
    CreditTierEnum,
    NetworkEnum,
    TransactionTypeEnum,
)


class BaseDBModel(BaseModel):
    id: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.astimezone(timezone.utc).isoformat()


class User(BaseDBModel):
    address: str
    total_credits: int = Field(default=0)
    remaining_credits: int = Field(default=0)


class App(BaseDBModel):
    name: str
    owner_id: Optional[str] = None
    type: AppTypeEnum = AppTypeEnum.THIRD_PARTY


class Auth(BaseDBModel):
    client_type: Optional[ClientTypeEnum] = Field(default=ClientTypeEnum.USER)
    hashed_key: str
    is_revoked: bool = False


class Credit(BaseDBModel):
    tier: CreditTierEnum
    value: float = Field(default=1.0)


class Transaction(BaseDBModel):
    app_id: Optional[str] = None
    user_id: Optional[str] = None
    type: TransactionTypeEnum
    amount: float


class Audit(BaseDBModel):
    job_id: str
    app_id: Optional[str] = None
    user_id: Optional[str] = None
    contract_id: str
    model: str
    audit_type: AuditTypeEnum
    processing_time_seconds: Optional[int] = None
    status: Optional[AuditStatusEnum] = Field(default=AuditStatusEnum.WAITING)
    raw_output: Optional[str] = None


class Contract(BaseDBModel):
    method: ContractMethodEnum
    is_available: bool = True
    n_retries: int = Field(default=0)
    next_attempt: datetime
    address: Optional[str] = None
    network: Optional[NetworkEnum] = None
    raw_code: Optional[str] = None
    hash_code: Optional[str] = None
