# flake8: noqa

from app.utils.schema.contract import ContractWithCodePydantic
from app.utils.schema.response import StaticAnalysisTokenResult, UploadContractResponse
from app.utils.schema.shared import ErrorResponse
from app.utils.types.openapi import OpenApiParams

GET_OR_CREATE_CONTRACT = OpenApiParams(
    summary="Contract get/create",
    description="""
Get or create a smart contract reference. `address` or `code` are required.
If `address` is provided, it will scan for the source code. Providing `network` will likely
speed up the response. If `code` is provided, it'll simply upload the raw code and create a reference
to it. Scanning requires that a smart contract is verified, and the source code is available. It is possible that
a given address exists on multiple chains, which is why `candidates` is provided.
        """,
    response_model=UploadContractResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)

GET_CONTRACT = OpenApiParams(
    summary="Get contract by id",
    description="Retrieve a previously uploaded contract by `id`",
    response_model=ContractWithCodePydantic,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)

ANALYZE_TOKEN = OpenApiParams(
    summary="Token static analysis",
    description="Upload a token contract to receive a static analysis",
    response_model=StaticAnalysisTokenResult,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
