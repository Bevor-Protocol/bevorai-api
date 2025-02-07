from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist

# from app.api.ai.webhook import process_webhook_replicate
from app.api.core.dependencies import require_auth
from app.api.services.ai import AiService
from app.schema.request import EvalBody
from app.schema.response import EvalResponse
from app.utils.enums import ResponseStructureEnum


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
            dependencies=[Depends(require_auth)],
        )
        self.router.add_api_route("/eval/{id}", self.get_eval_by_id, methods=["GET"])

    async def process_ai_eval(
        self,
        request: Request,
        data: EvalBody,
    ):
        response = await self.ai_service.process_evaluation(
            user=request.scope["auth"], data=data
        )

        return JSONResponse(response, status_code=202)

    async def get_eval_by_id(self, request: Request, id: str) -> EvalResponse:
        response_type = request.query_params.get(
            "response_type", ResponseStructureEnum.JSON.name
        )

        try:
            response_type = ResponseStructureEnum._value2member_map_[response_type]
        except Exception:
            raise HTTPException(
                status_code=400, detail="Invalid response_type parameter"
            )

        try:
            response = await self.ai_service.get_eval(id, response_type=response_type)
            return JSONResponse(
                response.model_dump()["result"]["result"], status_code=200
            )
        except DoesNotExist:
            return EvalResponse(
                success=False, exists=False, error="no record of this evaluation exists"
            )
