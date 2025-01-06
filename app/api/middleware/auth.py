import hashlib
import logging

from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from tortoise.exceptions import DoesNotExist

from app.db.models import Auth, User
from app.utils.enums import AppTypeEnum, ClientTypeEnum


class AuthenticationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/docs", "/openapi.json", "/", "/health"]:
            return await call_next(request)

        if "webhook" in request.url.path:
            return await call_next(request)

        use_identifier = request.url.path in ["/auth/user"]

        authorization = request.headers.get("authorization")
        address = request.headers.get("x-user-identifier")

        logging.info(f"REQUEST -- {authorization} --- {address}")

        if not authorization:
            raise HTTPException(
                status_code=401, detail="proper authorization headers not provided"
            )

        api_key = authorization.split(" ")[1]
        try:
            auth = await Auth.get(
                hashed_key=hashlib.sha256(api_key.encode()).hexdigest()
            ).select_related("user", "app__owner")

            if auth.is_revoked:
                raise HTTPException(status_code=401, detail="This token was revoked")

            # request made on behalf of themselves
            if auth.client_type == ClientTypeEnum.USER:
                request.state.user = auth.user
                request.state.require_credit_and_limit = True
            else:
                request.state.app = auth.app
                if auth.app.type == AppTypeEnum.FIRST_PARTY:
                    if use_identifier:
                        request.state.user = address
                    else:
                        user = await User.get(address=address)
                        request.state.user = user
                    request.state.require_credit_and_limit = False
                else:
                    request.state.require_credit_and_limit = True
                    if address:
                        if use_identifier:
                            request.state.user = address
                        else:
                            user = await User.get(address=address)
                            request.state.user = user
                    else:
                        request.state.user = auth.app.owner

        except DoesNotExist:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        except HTTPException as err:
            raise err

        response = await call_next(request)
        return response
