import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.core.dependencies import Authentication
from app.api.services.app import AppService
from app.api.services.auth import AuthService
from app.api.services.blockchain import BlockchainService
from app.api.services.user import UserService
from app.db.models import User
from app.schema.dependencies import AuthState
from app.schema.request import AppUpsertBody, UserUpsertBody
from app.utils.enums import AuthRequestScopeEnum, ClientTypeEnum


class AuthRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/auth", tags=["auth"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/user",
            self.get_or_create_user,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.APP))
            ],
        )
        self.router.add_api_route(
            "/generate/{client_type}",
            self.generate_api_key,
            methods=["POST"],
            dependencies=[
                Depends(
                    Authentication(request_scope=AuthRequestScopeEnum.APP_FIRST_PARTY)
                )
            ],
        )
        self.router.add_api_route(
            "/app",
            self.upsert_app,
            methods=["POST", "PATCH"],
            dependencies=[
                Depends(
                    Authentication(request_scope=AuthRequestScopeEnum.APP_FIRST_PARTY)
                )
            ],
        )
        self.router.add_api_route(
            "/sync/credits",
            self.sync_credits,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
        )

    async def get_or_create_user(
        self, request: Request, body: Annotated[UserUpsertBody, Body()]
    ):

        # Users are created through apps. A user is denoted by their address,
        # but might have different app owners that they were created through.
        user_service = UserService()

        response = await user_service.upsert_user(request.state.auth, body.address)

        return JSONResponse(
            {"user_id": str(response.id)}, status_code=status.HTTP_202_ACCEPTED
        )

    async def generate_api_key(self, request: Request, client_type: ClientTypeEnum):
        auth_service = AuthService()

        api_key = await auth_service.generate_auth(
            auth_obj=request.state.auth, client_type=client_type
        )

        return JSONResponse({"api_key": api_key}, status_code=status.HTTP_202_ACCEPTED)

    async def upsert_app(
        self, request: Request, body: Annotated[AppUpsertBody, Body()]
    ):
        app_service = AppService()

        if request.method == "POST":
            fct = app_service.create_app
        if request.method == "PATCH":
            fct = app_service.update_app

        response = await fct(auth=request.state.auth, body=body)

        return JSONResponse({"result": response}, status_code=status.HTTP_202_ACCEPTED)

    async def sync_credits(self, request: Request):
        blockchain_service = BlockchainService()

        auth: AuthState = request.state.auth
        try:
            user = await User.get(id=auth.user_id)
            credits = await blockchain_service.get_credits(user.address)
        except Exception as err:
            logging.exception(err)
            return JSONResponse(
                {"success": False, "error": "could not connect to network"},
                status_code=status.HTTP_200_OK,
            )

        prev_credits = user.total_credits
        user.total_credits = credits
        await user.save()

        return JSONResponse(
            {
                "total_credits": credits,
                "credits_added": max(0, credits - prev_credits),
                "credits_removed": max(
                    0, prev_credits - credits
                ),  # only applicable during refund.
            },
            status_code=status.HTTP_200_OK,
        )
