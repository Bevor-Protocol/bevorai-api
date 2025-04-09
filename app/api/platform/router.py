from fastapi import APIRouter, Depends, status

from app.api.dependencies import AuthenticationWithoutDelegation
from app.api.pricing.service import Usage
from app.utils.openapi_tags import PLATFORM_TAG
from app.utils.types.enums import RoleEnum

from .interface import GetCostEstimateResponse
from .openapi import GET_COST_ESTIMATE


class PlatformRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/platform", tags=[PLATFORM_TAG])

        self.add_api_route(
            "/cost-estimate",
            self.get_credit_estimate,
            methods=["GET"],
            dependencies=[
                Depends(AuthenticationWithoutDelegation(required_role=RoleEnum.USER))
            ],
            status_code=status.HTTP_200_OK,
            **GET_COST_ESTIMATE,
        )

    async def get_credit_estimate(self) -> GetCostEstimateResponse:
        usage = Usage()
        estimate = usage.estimate_pricing()
        return GetCostEstimateResponse(credits=estimate)
