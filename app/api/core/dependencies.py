"""
Acts a bit differently from middleware, as we inject these on a per-request
basis. Fundamentally acts as a middleware, but we have more control over when its
used without explicitly needing to whitelist / blacklist routes.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, Request, status
from tortoise.exceptions import DoesNotExist

from app.config import redis_client
from app.db.models import Auth, User
from app.schema.dependencies import AuthState
from app.utils.enums import (
    AppTypeEnum,
    AuthRequestScopeEnum,
    AuthScopeEnum,
    ClientTypeEnum,
)


class Authentication:
    """
    Defines the request authorization scope.
    Users can make requests only on behalf of themselves. The x-user-identifier header is ignored
    Apps can make requests on behalf of themselves, or users. If the x-user-identifier is used, then
        that corresponding user is injected. Otherwise, the App owner is used as the User
    First Party Apps can make requests on behalf of Users. First Party Apps have no "owner", so the
        x-user-identifier header is required to inject a user. Certain requests don't need
        a user.
    """  # noqa

    def __init__(
        self,
        request_scope: AuthRequestScopeEnum,
        scope_override: Optional[AuthScopeEnum] = None,
    ):
        self.request_scope = request_scope
        self.scope_override = scope_override

    async def _get_auth(self, request: Request) -> Auth:
        authorization = request.headers.get("authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="proper authorization headers not provided",
            )
        api_key = authorization.split(" ")[1]
        hashed_key = Auth.hash_key(api_key)
        logging.info(hashed_key)
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

    async def _infer_authentication(self, request: Request, auth: Auth):
        """
        Evaluation of the api key. Creates the request.state object as AuthState
        """
        identifier = request.headers.get("x-user-identifier")
        if self.request_scope in [
            AuthRequestScopeEnum.APP_FIRST_PARTY,
            AuthRequestScopeEnum.APP,
        ]:
            if auth.client_type != ClientTypeEnum.APP or not auth.app:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid api permissions",
                )

        if self.request_scope == AuthRequestScopeEnum.APP_FIRST_PARTY:
            if auth.app.type != AppTypeEnum.FIRST_PARTY:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid api permissions",
                )

        state = AuthState(client_type=auth.client_type, scope=auth.scope)

        # Apps are able to make requests on behalf of other users.
        if auth.client_type == ClientTypeEnum.APP:
            state.app_id = auth.app.id
            if identifier:
                state.is_delegator = True
                try:
                    user = await User.get(id=identifier)
                    state.user_id = user.id
                except DoesNotExist:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="user-identifier does not exist",
                    )
            else:
                if auth.app.type == AppTypeEnum.THIRD_PARTY:
                    user = auth.app.owner
                    state.user_id = user.id
        else:
            state.user_id = auth.user_id

        request.state.auth = state

    def _infer_authorization(self, request: Request, auth: Auth):
        """
        Evaluation of auth scope. If not overriden, will look at request.method
        """
        method = request.method
        cur_scope = auth.scope
        if not cur_scope:
            # only possible if authentication() is NotImplemented
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="incorrect scope for this request",
            )
        required_scope = self.scope_override
        if not required_scope:
            if method == "GET":
                required_scope = AuthScopeEnum.READ
            else:
                required_scope = AuthScopeEnum.WRITE

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

    # NOTE: if the arguments are anything other than request, it breaks.
    # ie, don't use *args, **kwargs
    async def __call__(self, request: Request) -> None:
        try:
            auth: Auth = await self._get_auth(request=request)
            await self._infer_authentication(request=request, auth=auth)
            self._infer_authorization(request=request, auth=auth)
            logging.info("PASSED AUTH")
        except Exception as err:
            logging.warning(err)
            raise err


class RateLimit:
    MAX_LIMIT_PER_MINUTE = 30
    WINDOW_SECONDS = 60

    def __init__(self):
        pass

    async def __call__(self, request: Request) -> None:
        auth: AuthState = request.state
        if auth["app"]:
            if auth["app"].type == AppTypeEnum.FIRST_PARTY:
                return

        authorization = request.headers.get("authorization")
        api_key = authorization.split(" ")[1]
        redis_key = f"rate_limit|{api_key}"

        current_time = int(datetime.now().timestamp())
        await redis_client.ltrim(redis_key, 0, self.MAX_LIMIT_PER_MINUTE)
        await redis_client.lrem(redis_key, 0, current_time - self.WINDOW_SECONDS)

        request_count = await redis_client.llen(redis_key)

        if request_count >= self.MAX_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests in a minute",
            )

        await redis_client.rpush(redis_key, current_time)
        await redis_client.expire(redis_client, self.WINDOW_SECONDS)
