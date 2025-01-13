from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from replicate.prediction import Prediction

from app.api.ai.eval import get_eval, process_evaluation
from app.api.ai.webhook import process_webhook_replicate
from app.api.depends.auth import UserDict, require_auth
from app.api.depends.rate_limit import rate_limit
from app.pydantic.request import EvalBody
from app.pydantic.response import EvalResponse
from app.utils.enums import ResponseStructureEnum


class AiRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/ai", tags=["ai"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/eval", self.process_ai_eval, methods=["POST"])
        self.router.add_api_route("/eval/{id}", self.get_eval_by_id, methods=["GET"])
        self.router.add_api_route(
            "/eval/webhook",
            self.process_webhook,
            methods=["POST"],
            include_in_schema=False,
        )

    async def process_ai_eval(
        self,
        request: Request,
        data: EvalBody,
        user: UserDict = Depends(require_auth),
    ):
        response = await process_evaluation(user=user, data=data)
        rate_limit(request=request, user=user)

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

        response = await get_eval(id, response_type=response_type)

        return JSONResponse(response.model_dump()["result"]["result"], status_code=200)

    async def process_webhook(self, request: Request):
        """
        Internal webhook endpoint for Replicate model predictions.
        This route should not be called directly - it is used by the Replicate service
        to deliver prediction results.
        """

        chained_call = request.query_params.get("chained_call")

        body = await request.json()
        response = await process_webhook_replicate(
            data=Prediction(**body), webhook_url=chained_call
        )
        return response
