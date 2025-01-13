from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.auth.generate import request_access
from app.api.auth.user import upsert_user
from app.api.depends.auth import require_app
from app.utils.enums import AppTypeEnum


class AuthRouter:
    def __init__(self):
        super().__init__()
        self.router = APIRouter(prefix="/auth", tags=["auth"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/api/request", self.request_access, methods=["POST"])
        self.router.add_api_route("/user", self.get_or_create_user, methods=["POST"])

    async def request_access(self, request: Request):
        # only accessible via the frontend dashboard
        if request.state.app:
            if request.state.app.type == AppTypeEnum.FIRST_PARTY:
                address = request.state.user
                response = request_access(address)

                return JSONResponse({"api_key": response}, status_code=200)

        raise HTTPException(status_code=401, detail="missing address header")

    async def get_or_create_user(self, user_identifier: str = Depends(require_app)):

        # Users can be created via apps, which all go through our first-party servicer

        response = await upsert_user(user_identifier)

        return JSONResponse({"user_id": str(response.id)}, status_code=200)
