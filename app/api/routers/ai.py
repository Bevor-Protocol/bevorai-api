from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status

from app.api.core.dependencies import Authentication, RequireCredits
from app.api.services.ai import AiService
from app.schema.request import EvalBody
from app.schema.response import CreateEvalResponse, GetCostEstimate, GetEvalResponse
from app.utils.enums import AuthRequestScopeEnum, ResponseStructureEnum
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
            response_model=CreateEvalResponse,
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER)),
                Depends(RequireCredits()),
            ],
        )
        self.router.add_api_route(
            "/eval/{id}",
            self.get_eval_by_id,
            methods=["GET"],
            response_model=GetEvalResponse,
            dependencies=[
                Depends(Authentication(request_scope=AuthRequestScopeEnum.USER))
            ],
        )
        self.router.add_api_route(
            "/credit/estimate",
            self.get_credit_estimate,
            response_model=GetCostEstimate,
            methods=["GET"],
        )

    async def process_ai_eval(
        self,
        request: Request,
        body: Annotated[EvalBody, Body()],
    ):
        return
        response = await self.ai_service.process_evaluation(
            auth=request.state.auth, data=body
        )

        return Response(response.model_dump_json(), status_code=status.HTTP_201_CREATED)

    async def get_eval_by_id(self, request: Request, id: str) -> GetEvalResponse:
        response_type = request.query_params.get(
            "response_type", ResponseStructureEnum.JSON.name
        )

        try:
            response_type = ResponseStructureEnum._value2member_map_[response_type]
        except Exception:
            raise HTTPException(
                status_code=400, detail="Invalid response_type parameter"
            )

        response = await self.ai_service.get_eval(
            auth=request.state.auth, id=id, response_type=response_type
        )
        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)

    async def get_credit_estimate(self):
        usage = Usage()
        estimate = usage.estimate_pricing()
        response = GetCostEstimate(credits=estimate)
        return Response(response.model_dump_json(), status_code=status.HTTP_200_OK)
