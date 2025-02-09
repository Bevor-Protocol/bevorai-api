from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.core.dependencies import authentication
from app.api.services.auth import AuthService
from app.api.services.user import UserService
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
                Depends(authentication(request_scope=AuthRequestScopeEnum.APP))
            ],
        )
        self.router.add_api_route(
            "/generate/{client_type}",
            self.generate_api_key,
            methods=["POST"],
            dependencies=[
                Depends(
                    authentication(request_scope=AuthRequestScopeEnum.APP_FIRST_PARTY)
                )
            ],
        )
        self.router.add_api_route(
            "/regenerate/{client_type}",
            self.regenerate_api_key,
            methods=["POST"],
            dependencies=[
                Depends(
                    authentication(request_scope=AuthRequestScopeEnum.APP_FIRST_PARTY)
                )
            ],
        )

    async def get_or_create_user(self, request: Request):

        # Users can be created via apps, which all go through our first-party servicer
        user_service = UserService()

        response = await user_service.upsert_user(request.scope["auth"])

        return JSONResponse({"user_id": str(response.id)}, status_code=200)

    async def generate_api_key(self, request: Request, client_type: ClientTypeEnum):
        auth_service = AuthService()

        api_key = await auth_service.generate_auth(
            address=request.scope["auth"], client_type=client_type
        )

        return JSONResponse({"api_key": api_key}, status_code=201)

    async def regenerate_api_key(self, request: Request, client_type: ClientTypeEnum):
        auth_service = AuthService()

        api_key = await auth_service.regenerate_auth(
            address=request.scope["auth"], client_type=client_type
        )

        return JSONResponse({"api_key": api_key}, status_code=201)
