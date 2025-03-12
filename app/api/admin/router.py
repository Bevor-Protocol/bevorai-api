import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.admin.service import AdminService
from app.api.dependencies import Authentication
from app.utils.schema.dependencies import AuthState
from app.utils.schema.request import AdminQuerySearch, UpdatePermissionsBody
from app.utils.schema.shared import BooleanResponse
from app.utils.types.enums import AuthScopeEnum, ClientTypeEnum, RoleEnum


class AdminRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/admin", include_in_schema=False)
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/status",
            self.is_admin,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(required_role=RoleEnum.APP_FIRST_PARTY))
            ],
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/search/app",
            self.search_apps,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(required_role=RoleEnum.APP_FIRST_PARTY))
            ],
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/search/user",
            self.search_users,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(required_role=RoleEnum.APP_FIRST_PARTY))
            ],
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/permissions/{client_type}/{id}",
            self.update_permissions,
            methods=["POST"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
            include_in_schema=False,
        )

    async def is_admin(self, request: Request):
        admin_service = AdminService()

        auth: AuthState = request.state.auth

        is_admin = await admin_service.is_admin(auth)
        if not is_admin:
            logging.warn(f"unauthenticated attempt at admin access {auth.user_id}")

        return Response(
            BooleanResponse(success=is_admin).model_dump_json(),
            status_code=status.HTTP_202_ACCEPTED,
        )

    async def search_users(
        self,
        query_params: Annotated[AdminQuerySearch, Query()],
    ):
        admin_service = AdminService()

        results = await admin_service.search_users(identifier=query_params.identifier)

        return JSONResponse({"results": results}, status_code=status.HTTP_200_OK)

    async def search_apps(
        self,
        query_params: Annotated[AdminQuerySearch, Query()],
    ):
        admin_service = AdminService()

        results = await admin_service.search_apps(identifier=query_params.identifier)

        return JSONResponse({"results": results}, status_code=status.HTTP_200_OK)

    async def update_permissions(
        self,
        body: Annotated[UpdatePermissionsBody, Body()],
        client_type: ClientTypeEnum,
        id: str,
    ):
        admin_service = AdminService()

        await admin_service.update_permissions(
            id=id, client_type=client_type, data=body
        )

        return Response(
            BooleanResponse(success=True).model_dump_json(),
            status_code=status.HTTP_202_ACCEPTED,
        )
