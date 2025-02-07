from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.core.dependencies import require_app
from app.api.services.auth import AuthService
from app.api.services.user import UserService
from app.utils.enums import AppTypeEnum


class AuthRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/auth", tags=["auth"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/api/request", self.request_access, methods=["POST"])
        self.router.add_api_route(
            "/user",
            self.get_or_create_user,
            methods=["POST"],
            dependencies=[Depends(require_app)],
        )

    async def request_access(self, request: Request):
        # only accessible via the frontend dashboard
        auth_service = AuthService()
        if request.state.app:
            if request.state.app.type == AppTypeEnum.FIRST_PARTY:
                address = request.state.user
                response = auth_service.request_access(address)

                return JSONResponse({"api_key": response}, status_code=200)

        raise HTTPException(status_code=401, detail="missing address header")

    async def get_or_create_user(self, request: Request):

        # Users can be created via apps, which all go through our first-party servicer
        user_service = UserService()

        response = await user_service.upsert_user(request.scope["auth"])

        return JSONResponse({"user_id": str(response.id)}, status_code=200)
