"""
Acts a bit differently from middleware, as we inject these on a per-request
basis. Fundamentally acts as a middleware, but we have more control over when its
used without explicitly needing to whitelist / blacklist routes.
"""

from datetime import datetime
from typing import Callable, Optional

from fastapi import HTTPException, Request, status
from tortoise.exceptions import DoesNotExist

from app.config import redis_client
from app.db.models import Auth, User
from app.schema.dependencies import AuthDict
from app.utils.enums import (
    AppTypeEnum,
    AuthRequestScopeEnum,
    AuthScopeEnum,
    ClientTypeEnum,
)

MAX_LIMIT_PER_MINUTE = 30
WINDOW_SECONDS = 60


async def get_auth(authorization: Optional[str]) -> Auth:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="proper authorization headers not provided",
        )
    api_key = authorization.split(" ")[1]
    hashed_key = Auth.hash_key(api_key)
    try:
        auth = await Auth.get(hashed_key=hashed_key).select_related(
            "user", "app__owner"
        )
    except DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key"
        )
    if auth.revoked_at:
        raise HTTPException(status_code=401, detail="This token was revoked")

    return auth


def authentication(request_scope: AuthRequestScopeEnum) -> Callable:
    """
    Defines the request authorization scope.
    Users can make requests only on behalf of themselves. The x-user-identifier header is ignored
    Apps can make requests on behalf of themselves, or users. If the x-user-identifier is used, then
        that corresponding user is injected. Otherwise, the App owner is used as the User
    First Party Apps can make requests on behalf of Users. First Party Apps have no "owner", so the
        x-user-identifier header is required to inject a user. Certain requests don't need
        a user.
    """  # noqa

    async def _authentication(request: Request) -> None:
        authorization = request.headers.get("authorization")
        identifier = request.headers.get("x-user-identifier")

        auth = await get_auth(authorization)

        if request_scope in [
            AuthRequestScopeEnum.APP_FIRST_PARTY,
            AuthRequestScopeEnum.APP,
        ]:
            if auth.client_type != ClientTypeEnum.APP or not auth.app:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid api permissions",
                )

        if request_scope == AuthRequestScopeEnum.APP_FIRST_PARTY:
            if auth.app.type != AppTypeEnum.FIRST_PARTY:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid api permissions",
                )

        state = AuthDict(client_type=auth.client_type, scope=auth.scope)

        # Apps are able to make requests on behalf of other users.
        if auth.client_type == ClientTypeEnum.APP:
            state["app"] = auth.app
            if identifier:
                state["is_delegator"] = True
                try:
                    user = await User.get(id=identifier)
                    state["user"] = user
                except DoesNotExist:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="user-identifier does not exist",
                    )
            else:
                if auth.app.type == AppTypeEnum.THIRD_PARTY:
                    user = auth.app.owner
                    state["user"] = user
        else:
            user = auth.user
            state["user"] = user

        request.state = state

    return _authentication


def scope(required_scope: AuthScopeEnum):
    async def _scope(request: Request):
        cur_scope = request.state.get("scope")
        if not cur_scope:
            # only possible if authentication() is NotImplemented
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="incorrect scope for this request",
            )

        cur_scope: AuthScopeEnum
        if required_scope == AuthScopeEnum.ADMIN:
            if cur_scope != AuthScopeEnum.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="incorrect scope for this request",
                )
        if required_scope == AuthScopeEnum.WRITE:
            if cur_scope not in [AuthScopeEnum.ADMIN, AuthScopeEnum.WRITE]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="incorrect scope for this request",
                )

    return _scope


async def rate_limit(request: Request, auth: AuthDict) -> None:
    if auth["app"]:
        if auth["app"].type == AppTypeEnum.FIRST_PARTY:
            return
    bearer = request.headers.get("authorization")
    api_key = bearer.split(" ")[1]
    redis_key = f"rate_limit|{api_key}"

    current_time = int(datetime.now().timestamp())
    await redis_client.ltrim(redis_key, 0, MAX_LIMIT_PER_MINUTE)
    await redis_client.lrem(redis_key, 0, current_time - WINDOW_SECONDS)

    request_count = await redis_client.llen(redis_key)

    if request_count >= MAX_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too many requests in a minute")

    await redis_client.rpush(redis_key, current_time)
    await redis_client.expire(redis_client, WINDOW_SECONDS)
