from fastapi import APIRouter, Depends, Response, status

from app.api.core.dependencies import AuthenticationWithoutDelegation
from app.api.pricing.service import Usage
from app.utils.openapi import OPENAPI_SPEC
from app.utils.schema.response import GetCostEstimateResponse
from app.utils.types.enums import AuthRequestScopeEnum


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
                Depends(
                    AuthenticationWithoutDelegation(
                        request_scope=AuthRequestScopeEnum.USER
                    )
                )
            ],
            **OPENAPI_SPEC["get_cost_estimate"]
        )

    async def get_credit_estimate(self):
        usage = Usage()
        estimate = usage.estimate_pricing()
        response = GetCostEstimateResponse(credits=estimate)
        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
