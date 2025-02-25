from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status

from app.api.core.dependencies import AuthenticationWithoutDelegation, RequireCredits
from app.api.services.static_analyzer import StaticAnalysisService
from app.schema.request import ContractScanBody
from app.utils.enums import AuthRequestScopeEnum
from app.utils.openapi import OPENAPI_SPEC


class StaticRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/static", tags=["static"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/token",
            self.process_token,
            methods=["POST"],
            dependencies=[
                Depends(
                    AuthenticationWithoutDelegation(
                        request_scope=AuthRequestScopeEnum.USER
                    )
                ),
                Depends(RequireCredits()),
            ],
            **OPENAPI_SPEC["analyze_token"],
        )

    async def process_token(
        self,
        request: Request,
        body: Annotated[ContractScanBody, Body()],
    ):
        sa_service = StaticAnalysisService()
        response = await sa_service.process_static_eval_token(body)

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
