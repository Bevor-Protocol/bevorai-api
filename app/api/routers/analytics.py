from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.api.core.dependencies import Authentication
from app.api.services.audit import AuditService
from app.api.services.user import UserService
from app.schema.request import FeedbackBody, FilterParams
from app.schema.response import AnalyticsResponse
from app.utils.enums import AuthRequestScopeEnum


def _parse_query_params(request: Request) -> FilterParams:
    """
    Parses query parameters from the request
    and returns them as a QueryParams object.
    """
    query = FilterParams()

    for k, v in query.model_dump().items():
        value = request.query_params.get(k)
        if not value:
            continue
        if isinstance(v, list):
            setattr(query, k, value.split(","))
        elif isinstance(v, int):
            setattr(query, k, int(value))
        elif isinstance(v, str):
            setattr(query, k, value)
        # Add more type checks as necessary for other types
        else:
            setattr(query, k, value)

    return query


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
        )
        self.router.add_api_route(
            "/audit/{id}",
            self.get_audit,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
        )
        self.router.add_api_route(
            "/feedback",
            self.submit_feedback,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
        )
        self.router.add_api_route(
            "/user",
            self.get_user_info,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
        )

    async def fetch_audits(
        self,
        request: Request,
        query_params: Annotated[FilterParams, Query()],
    ) -> AnalyticsResponse:
        # rate_limit(request=request, user=user)
        audit_service = AuditService()
        response = await audit_service.get_audits(
            auth=request.state.auth,
            query=query_params,
        )

        return JSONResponse(response.model_dump(), status_code=200)

    async def fetch_stats(self) -> AnalyticsResponse:
        audit_service = AuditService()
        response = await audit_service.get_stats()

        return JSONResponse(response.model_dump(), status_code=200)

    async def get_audit(self, request: Request, id: str):
        audit_service = AuditService()
        audit = await audit_service.get_audit(user=request.state.auth, id=id)

        return JSONResponse({"result": audit}, status_code=200)

    async def get_user_info(self, request: Request):
        user_service = UserService()
        user_info = await user_service.get_user_info(request.state.auth)
        return JSONResponse(user_info.model_dump(), status_code=200)

    async def submit_feedback(self, request: Request, data: FeedbackBody):
        audit_service = AuditService()
        response = await audit_service.submit_feeback(
            data=data, user=request.state.auth
        )
        return JSONResponse({"success": response}, status_code=200)
