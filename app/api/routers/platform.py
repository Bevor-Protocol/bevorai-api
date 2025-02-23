from fastapi import APIRouter, Depends, Response, status

from app.api.core.dependencies import Authentication
from app.api.services.audit import AuditService
from app.schema.response import AnalyticsResponse, GetCostEstimateResponse
from app.utils.enums import AuthRequestScopeEnum
from app.utils.openapi import OPENAPI_SPEC
from app.utils.pricing import Usage


class PlatformRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/platform", tags=["platform"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/cost-estimate",
            self.get_credit_estimate,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_cost_estimate"]
        )

    async def get_credit_estimate(self):
        usage = Usage()
        estimate = usage.estimate_pricing()
        response = GetCostEstimateResponse(credits=estimate)
        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)

    async def fetch_stats(self) -> AnalyticsResponse:
        audit_service = AuditService()
        response = await audit_service.get_stats()

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
