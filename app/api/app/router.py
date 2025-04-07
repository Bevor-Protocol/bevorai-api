from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.exceptions import HTTPException
from tortoise.exceptions import DoesNotExist

from app.api.dependencies import Authentication, AuthenticationWithoutDelegation
from app.utils.openapi_tags import APP_TAG
from app.utils.types.shared import AuthState
from app.utils.types.shared import BooleanResponse
from app.utils.types.enums import RoleEnum

from .interface import AllStatsResponse, AppInfoResponse, AppUpsertBody
from .openapi import GET_APP_INFO
from .service import AppService


class AppRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/app", tags=[APP_TAG])

        self.add_api_route(
            "",
            self.upsert_app,
            methods=["POST", "PATCH"],
            dependencies=[
                Depends(Authentication(required_role=RoleEnum.APP_FIRST_PARTY))
            ],
            operation_id="upsert_app",
            status_code=status.HTTP_202_ACCEPTED,
            include_in_schema=False,
        )
        self.add_api_route(
            "/info",
            self.get_app_info,
            methods=["GET"],
            dependencies=[
                Depends(AuthenticationWithoutDelegation(required_role=RoleEnum.APP))
            ],
            status_code=status.HTTP_200_OK,
            **GET_APP_INFO,
        )
        self.add_api_route(
            "/stats",
            self.get_stats,
            methods=["GET"],
            dependencies=[
                Depends(
                    AuthenticationWithoutDelegation(
                        required_role=RoleEnum.APP_FIRST_PARTY
                    )
                )
            ],
            status_code=status.HTTP_200_OK,
            include_in_schema=False,
        )

    async def upsert_app(
        self, request: Request, body: Annotated[AppUpsertBody, Body()]
    ) -> BooleanResponse:
        app_service = AppService()

        if request.method == "POST":
            fct = app_service.create
        if request.method == "PATCH":
            fct = app_service.update

        try:
            await fct(auth=request.state.auth, body=body)
            return BooleanResponse(success=True)
        except DoesNotExist as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    async def get_app_info(self, request: Request) -> AppInfoResponse:
        app_service = AppService()
        auth: AuthState = request.state.auth

        try:
            response = await app_service.get_info(auth.app_id)
            return response
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="This app does not exist"
            )

    async def get_stats(self) -> AllStatsResponse:
        app_service = AppService()

        response = await app_service.get_stats()

        return response
