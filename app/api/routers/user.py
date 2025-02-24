from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status

from app.api.core.dependencies import Authentication
from app.api.services.user import UserService
from app.schema.request import UserUpsertBody
from app.schema.response import IdResponse
from app.utils.enums import AuthRequestScopeEnum
from app.utils.openapi import OPENAPI_SPEC


class UserRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/user", tags=["user"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "",
            self.get_or_create_user,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.APP))
            ],
            **OPENAPI_SPEC["get_or_create_user"]
        )
        self.router.add_api_route(
            "/info",
            self.get_user_info,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_user_info"]
        )

    async def get_or_create_user(
        self, request: Request, body: Annotated[UserUpsertBody, Body()]
    ):

        # Users are created through apps. A user is denoted by their address,
        # but might have different app owners that they were created through.
        user_service = UserService()

        result = await user_service.get_or_create(request.state.auth, body.address)
        response = IdResponse(id=result.id)

        return Response(
            response.model_dump_json(), status_code=status.HTTP_202_ACCEPTED
        )

    async def get_user_info(self, request: Request):
        user_service = UserService()
        user_info = await user_service.get_info(request.state.auth)
        return Response(user_info.model_dump_json(), status_code=status.HTTP_200_OK)
