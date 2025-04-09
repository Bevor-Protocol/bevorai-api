from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.utils.types.common import ModelId, NullableModelId
from app.utils.types.enums import RoleEnum
from app.utils.types.mixins import FkMixin, IdMixin


class IdResponse(BaseModel, IdMixin):
    id: ModelId


class Timeseries(BaseModel):
    date: str
    count: int


class BooleanResponse(BaseModel):
    success: bool


class ErrorResponse(BaseModel):
    detail: str


T = TypeVar("T")


class ResultsResponse(BaseModel, Generic[T]):
    results: list[T] = Field(default_factory=lambda: [])


class AuthState(BaseModel, FkMixin):
    user_id: NullableModelId = None
    app_id: NullableModelId = None
    consumes_credits: bool
    credit_consumer_user_id: NullableModelId = None
    is_delegated: bool = False
    role: RoleEnum
