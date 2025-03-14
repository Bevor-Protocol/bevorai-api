# flake8: noqa

from app.utils.schema.response import GetCostEstimateResponse
from app.utils.schema.shared import ErrorResponse
from app.utils.types.openapi import OpenApiParams

GET_COST_ESTIMATE = OpenApiParams(
    summary="Get current cost estimate",
    description="Can be used to infer current cost of running an eval. Response is in terms of credits.",
    response_model=GetCostEstimateResponse,
    responses={401: {"model": ErrorResponse}},
)
