from fastapi import APIRouter, HTTPException, Request

from app.api.ai.eval import get_eval, process_evaluation
from app.api.ai.webhook import process_webhook_replicate
from app.pydantic.request import EvalBody
from app.pydantic.response import EvalResponse
from app.utils.enums import ResponseStructureEnum


class AiRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/ai", tags=["ai"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/eval", self.evaluate_contract_raw, methods=["POST"])
        self.router.add_api_route("/eval/{id}", self.get_eval_by_id, methods=["GET"])
        self.router.add_api_route(
            "/eval/webhook", self.process_webhook, methods=["POST"]
        )

    async def evaluate_contract_raw(self, request: Request, data: EvalBody):
        return await process_evaluation(request.state.user, data)

    async def get_eval_by_id(self, request: Request, id: str) -> EvalResponse:
        response_type = request.query_params.get(
            "response_type", ResponseStructureEnum.JSON.name
        )
        try:
            response_type = ResponseStructureEnum[response_type]
        except Exception:
            raise HTTPException(
                status_code=400, detail="Invalid response_type parameter"
            )
        return await get_eval(id, response_type=response_type)

    async def process_webhook(self, request: Request):
        """
        Internal webhook endpoint for Replicate model predictions.
        This route should not be called directly - it is used by the Replicate service
        to deliver prediction results.
        """

        response_type = request.query_params.get("response_type")
        chained_call = request.query_params.get("chained_call")

        body = await request.json()
        return await process_webhook_replicate(
            data=body, response_type=response_type, webhook_url=chained_call
        )
