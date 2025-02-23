from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.core.dependencies import Authentication
from app.api.services.app import AppService
from app.api.services.audit import AuditService
from app.schema.request import AppUpsertBody
from app.utils.enums import AuthRequestScopeEnum
from app.utils.openapi import OPENAPI_SPEC


class AppRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/app", tags=["app"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/",
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
            fct = app_service.create_app
        if request.method == "PATCH":
            fct = app_service.update_app

        response = await fct(auth=request.state.auth, body=body)

        return JSONResponse({"result": response}, status_code=status.HTTP_202_ACCEPTED)

    async def get_app_info(self, request: Request):
        # TODO: fix this.
        audit_service = AuditService()
        response = await audit_service.get_stats()

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
