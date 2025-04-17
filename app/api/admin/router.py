from typing import Annotated

import logfire
from fastapi import APIRouter, Body, Depends, Query, Request, Response, status

from app.api.dependencies import Authentication
from app.utils.types.enums import AuthScopeEnum, ClientTypeEnum, RoleEnum
from app.utils.types.models import PromptSchema
from app.utils.types.relations import AppPermissionRelation, UserPermissionRelation
from app.utils.types.shared import (
    AuthState,
    BooleanResponse,
    IdResponse,
    ResultsResponse,
)

from .interface import (
    AdminQuerySearch,
    AuditWithResult,
    CreatePromptBody,
    UpdatePermissionsBody,
    UpdatePromptBody,
)
from .service import AdminService


class AdminRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/admin", include_in_schema=False)

        self.add_api_route(
            "/status",
            self.is_admin,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(required_role=RoleEnum.APP_FIRST_PARTY))
            ],
            status_code=status.HTTP_200_OK,
        )
        self.add_api_route(
            "/search/app",
            self.search_apps,
            methods=["GET"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
            status_code=status.HTTP_200_OK,
        )
        self.add_api_route(
            "/search/user",
            self.search_users,
            methods=["GET"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
            status_code=status.HTTP_200_OK,
        )
        self.add_api_route(
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
            status_code=status.HTTP_202_ACCEPTED,
        )
        self.add_api_route(
            "/prompts",
            self.get_prompts,
            methods=["GET"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
            status_code=status.HTTP_200_OK,
        )
        self.add_api_route(
            "/prompt/{id}",
            self.update_prompt,
            methods=["PATCH"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
            status_code=status.HTTP_202_ACCEPTED,
        )
        self.add_api_route(
            "/prompt",
            self.add_prompt,
            methods=["POST"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
            status_code=status.HTTP_202_ACCEPTED,
        )
        self.add_api_route(
            "/audit/{id}",
            self.get_audit,
            methods=["GET"],
            dependencies=[
                Depends(
                    Authentication(
                        required_role=RoleEnum.APP_FIRST_PARTY,
                        delegated_scope=AuthScopeEnum.ADMIN,
                    )
                )
            ],
            status_code=status.HTTP_200_OK,
        )

    async def is_admin(self, request: Request) -> BooleanResponse:
        admin_service = AdminService()

        auth: AuthState = request.state.auth

        is_admin = await admin_service.is_admin(auth)
        if not is_admin:
            logfire.warning("unauthenticated attempt at admin access")

        return BooleanResponse(success=is_admin)

    async def search_users(
        self,
        query_params: Annotated[AdminQuerySearch, Query()],
    ) -> ResultsResponse[UserPermissionRelation]:
        admin_service = AdminService()

        results = await admin_service.search_users(identifier=query_params.identifier)

        return ResultsResponse[UserPermissionRelation](results=results)

    async def search_apps(
        self,
        query_params: Annotated[AdminQuerySearch, Query()],
    ) -> ResultsResponse[AppPermissionRelation]:
        admin_service = AdminService()

        results = await admin_service.search_apps(identifier=query_params.identifier)

        return ResultsResponse[AppPermissionRelation](results=results)

    async def update_permissions(
        self,
        body: Annotated[UpdatePermissionsBody, Body()],
        client_type: ClientTypeEnum,
        id: str,
    ) -> BooleanResponse:
        admin_service = AdminService()

        await admin_service.update_permissions(
            id=id, client_type=client_type, body=body
        )

        return BooleanResponse(success=True)

    async def get_prompts(self) -> ResultsResponse[PromptSchema]:
        admin_service = AdminService()

        prompts = await admin_service.get_prompts()

        return ResultsResponse[PromptSchema](results=prompts)

    async def update_prompt(
        self, body: Annotated[UpdatePromptBody, Body()], id: str
    ) -> BooleanResponse:
        admin_service = AdminService()

        try:
            await admin_service.update_prompt(body=body, id=id)
            return BooleanResponse(success=True)
        except Exception:
            return Response(
                BooleanResponse(success=False).model_dump_json(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    async def add_prompt(self, body: Annotated[CreatePromptBody, Body()]) -> IdResponse:
        admin_service = AdminService()

        prompt = await admin_service.add_prompt(body=body)
        return IdResponse(id=prompt.id)

    async def get_audit(self, id: str) -> AuditWithResult:
        admin_service = AdminService()

        audit = await admin_service.get_audit_children(id)
        return audit
