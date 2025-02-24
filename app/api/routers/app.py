from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.core.dependencies import Authentication
from app.api.services.app import AppService
from app.schema.dependencies import AuthState
from app.schema.request import AppUpsertBody
from app.utils.enums import AuthRequestScopeEnum, AuthScopeEnum
from app.utils.openapi import OPENAPI_SPEC


class AppRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/app", tags=["app"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "",
            self.upsert_app,
            methods=["POST", "PATCH"],
            dependencies=[
                Depends(
                    Authentication(request_scope=AuthRequestScopeEnum.APP_FIRST_PARTY)
                )
            ],
            operation_id="upsert_app",
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/info",
            self.get_app_info,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.APP))
            ],
            **OPENAPI_SPEC["get_app_info"]
        )

    async def upsert_app(
        self, request: Request, body: Annotated[AppUpsertBody, Body()]
    ):
        app_service = AppService()

        if request.method == "POST":
            fct = app_service.create
        if request.method == "PATCH":
            fct = app_service.update

        response = await fct(auth=request.state.auth, body=body)

        return JSONResponse({"result": response}, status_code=status.HTTP_202_ACCEPTED)

    async def get_app_info(self, request: Request):
        app_service = AppService()

        app_id = None
        auth: AuthState = request.state.auth
        # This call is scoped to the APP level, ignore is_delegator and user_id info.
        if auth.scope != AuthScopeEnum.ADMIN:
            app_id = auth.app_id

        response = await app_service.get_stats(app_id)

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
