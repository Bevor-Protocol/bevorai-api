from typing import Optional

from pydantic import BaseModel

from app.utils.schema.shared import CreatedAtResponse, IdResponse

"""
Used for HTTP request validation, response Serialization, and arbitrary typing.
"""


class UserUpsertBody(BaseModel):
    address: str


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
