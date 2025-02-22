from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request, Response, status

from app.api.core.dependencies import Authentication, RequireCredits
from app.api.services.ai import AiService
from app.schema.request import EvalBody, EvalParams
from app.schema.response import GetCostEstimate
from app.utils.enums import AuthRequestScopeEnum
from app.utils.openapi import OPENAPI_SPEC
from app.utils.pricing import Usage


class AiRouter:
    ai_service = AiService()

    def __init__(self):
        self.router = APIRouter(prefix="/ai", tags=["ai"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route(
            "/eval",
            self.process_ai_eval,
            methods=["POST"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER)),
                Depends(RequireCredits()),
            ],
            **OPENAPI_SPEC["start_eval"]
        )
        self.router.add_api_route(
            "/eval/{id}",
            self.get_eval_by_id,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_eval"]
        )
        self.router.add_api_route(
            "/eval/{id}/steps",
            self.get_eval_steps_by_id,
            methods=["GET"],
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
            **OPENAPI_SPEC["get_eval_steps"]
        )
        self.router.add_api_route(
            "/credit/estimate",
            self.get_credit_estimate,
            methods=["GET"],
            **OPENAPI_SPEC["cost_estimate"]
        )

    async def process_ai_eval(
        self,
        request: Request,
        body: Annotated[EvalBody, Body()],
    ):
        response = await self.ai_service.process_evaluation(
            auth=request.state.auth, data=body
        )

        return Response(response.model_dump_json(), status_code=status.HTTP_201_CREATED)

    async def get_eval_by_id(
        self, request: Request, id: str, query_params: Annotated[EvalParams, Query()]
    ):

        response = await self.ai_service.get_eval(
            auth=request.state.auth, id=id, response_type=query_params.response_type
        )
        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)

    async def get_eval_steps_by_id(self, request: Request, id: str):
        response = await self.ai_service.get_eval_steps(id=id)

        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)

    async def get_credit_estimate(self):
        usage = Usage()
        estimate = usage.estimate_pricing()
        response = GetCostEstimate(credits=estimate)
        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
