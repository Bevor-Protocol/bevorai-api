from app.utils.types.openapi import OpenApiParams
from app.utils.types.shared import ErrorResponse

from .interface import AppInfoResponse

GET_APP_INFO = OpenApiParams(
    summary="Get App Info",
    description="Get App-level information. Only callable as an `App`.",
    response_model=AppInfoResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
