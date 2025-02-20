from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.core.dependencies import Authentication
from app.api.services.audit import AuditService
from app.api.services.user import UserService
from app.schema.request import FeedbackBody, FilterParams
from app.schema.response import AnalyticsResponse
from app.utils.enums import AuthRequestScopeEnum
from app.utils.openapi import OPENAPI_SPEC


class AnalyticsRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/analytics", tags=["analytics"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/audits",
            self.fetch_audits,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_audits"]
        )
        self.router.add_api_route(
            "/stats",
            self.fetch_stats,
            methods=["GET"],
            dependencies=[
                Depends(
                    Authentication(request_scope=AuthRequestScopeEnum.APP_FIRST_PARTY)
                )
            ],
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/audit/{id}",
            self.get_audit,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_audit"]
        )
        self.router.add_api_route(
            "/feedback",
            self.submit_feedback,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["submit_feedback"]
        )
        self.router.add_api_route(
            "/user",
            self.get_user_info,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            include_in_schema=False,
        )

    async def fetch_audits(
        self,
        request: Request,
        query_params: Annotated[FilterParams, Query()],
    ):
        # rate_limit(request=request, user=user)
        audit_service = AuditService()
        response = await audit_service.get_audits(
            auth=request.state.auth,
            query=query_params,
        )

        return JSONResponse(response.model_dump(), status_code=status.HTTP_200_OK)

    async def fetch_stats(self) -> AnalyticsResponse:
        audit_service = AuditService()
        response = await audit_service.get_stats()

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)

    async def get_audit(self, request: Request, id: str):
        audit_service = AuditService()
        audit = await audit_service.get_audit(auth=request.state.auth, id=id)

        return Response(audit.model_dump_json(), status_code=status.HTTP_200_OK)

    async def get_user_info(self, request: Request):
        user_service = UserService()
        user_info = await user_service.get_user_info(request.state.auth)
        return Response(user_info.model_dump_json(), status_code=status.HTTP_200_OK)

    async def submit_feedback(self, request: Request, data: FeedbackBody):
        audit_service = AuditService()
        response = await audit_service.submit_feedback(
            data=data, user=request.state.auth
        )
        return JSONResponse({"success": response}, status_code=status.HTTP_201_CREATED)
