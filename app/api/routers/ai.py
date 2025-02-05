from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.ai.eval import EvalService

# from app.api.ai.webhook import process_webhook_replicate
from app.api.depends.auth import UserDict, require_auth
from app.api.depends.rate_limit import rate_limit
from app.pydantic.request import EvalBody
from app.pydantic.request import EvalAgentBody
from app.pydantic.response import EvalResponse
from app.utils.enums import ResponseStructureEnum


class AiRouter:

    def __init__(self):
        self.router = APIRouter(prefix="/ai", tags=["ai"])
        self.register_routes()

    def register_routes(self):
        self.router.add_api_route("/eval", self.process_ai_eval, methods=["POST"])
        self.router.add_api_route(
            "/eval/agent", self.process_agent_eval, methods=["POST"]
        )
        self.router.add_api_route("/eval/{id}", self.get_eval_by_id, methods=["GET"])
        # self.router.add_api_route(
        #     "/eval/webhook",
        #     self.process_webhook,
        #     methods=["POST"],
        #     include_in_schema=False,
        # )

    async def process_ai_eval(
        self,
        request: Request,
        data: EvalBody,
        user: UserDict = Depends(require_auth),
    ):
        await rate_limit(request=request, user=user)
        eval_service = EvalService()
        response = await eval_service.process_evaluation(user=user, data=data)

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

        eval_service = EvalService()

        response = await eval_service.get_eval(id, response_type=response_type)

        return JSONResponse(response.model_dump()["result"]["result"], status_code=200)

    async def process_agent_eval(
        self,
        request: Request,
        data: EvalAgentBody,
        user: UserDict = Depends(require_auth),
    ):
        await rate_limit(request=request, user=user)
        eval_service = EvalService()

        # Get base evaluation first
        # base_response = await eval_service.process_evaluation(user=user, data=data)

        # Calculate agent security score components
        mindshare_score = 75.0  # TODO: Calculate from twitter_handle engagement
        larp_probability = 25.0  # TODO: Calculate from cookiedao_link reputation
        market_cap = 50_000_000  # TODO: Get from market data

        # Get audit score from base evaluation
        audit_score = 85.0  # TODO: Extract from base_response

        # Calculate final security score using formula
        security_score = (
            (0.3 * mindshare_score)
            + (0.2 * (100 - larp_probability))
            + (0.2 * (math.log10(1 + min(market_cap, 100_000_000)) / math.log10(101)))
            + (0.3 * audit_score)
        )

        # Add security score to response
        response = {
            # **base_response,
            "agent_security_score": round(security_score, 2),
            "score_components": {
                "mindshare": mindshare_score,
                "larp_probability": larp_probability,
                "market_cap": market_cap,
                "audit_score": audit_score,
            },
        }

        return JSONResponse(response, status_code=202)

    def extract_agent_name(self, url: str) -> str:
        """
        Extracts agent name from a cookie.fun URL

        Args:
            url: URL in format https://www.cookie.fun/en/agent/{agent_name}

        Returns:
            The agent name string
        """
        try:
            # Split URL by '/' and get the last segment
            segments = url.rstrip("/").split("/")
            return segments[-1]
        except:
            raise ValueError(
                "Invalid URL format. Expected https://www.cookie.fun/en/agent/{agent_name}"
            )

    # async def process_webhook(self, request: Request):
    #     """
    #     Internal webhook endpoint for Replicate model predictions.
    #     This route should not be called directly - it is used by the Replicate service
    #     to deliver prediction results.
    #     """

    #     chained_call = request.query_params.get("chained_call")

    #     body = await request.json()
    #     response = await process_webhook_replicate(
    #         data=Prediction(**body), webhook_url=chained_call
    #     )
    #     return response
