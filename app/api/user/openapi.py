# flake8: noqa

from app.utils.types.shared import ErrorResponse, IdResponse
from app.utils.types.openapi import OpenApiParams

from .interface import UserInfoResponse

GET_OR_CREATE_USER = OpenApiParams(
    summary="Create a user",
    description="Only callable from an authenticated `App`. If already exists, will return the user `id`.",
    response_model=IdResponse,
    responses={401: {"model": ErrorResponse}},
)

GET_USER_INFO = OpenApiParams(
    summary="Get User info",
    description="Get user stats. Callable as an `App` using the `Bevor-User-Identifier`, or as a `User`",
    response_model=UserInfoResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
