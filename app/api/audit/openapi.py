# flake8: noqa

from app.utils.types.shared import BooleanResponse, ErrorResponse
from app.utils.types.openapi import OpenApiParams

from .interface import (
    AuditResponse,
    AuditsResponse,
    CreateEvalResponse,
    GetAuditStatusResponse,
)

CREATE_AUDIT = OpenApiParams(
    summary="Create AI eval",
    description="""
Initializes an AI smart contract audit. `contract_id` is the referenced contract obtained
from [`POST /contract`](/docs#tag/contract/operation/upload_contract_contract__post).
`audit_type` is of type `AuditTypeEnum`.\n\n
Note, that this **consumes credits**.
        """,
    response_model=CreateEvalResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)

GET_AUDITS = OpenApiParams(
    summary="Get audits",
    description="""
        Get audits according to a filter set. If calling as an `App`, you'll be able to view all audits generated
        through your app. If calling as a `User`, you'll be able to view your own audits (making `user_id` or `user_address` irrelevant).
        """,
    response_model=AuditsResponse,
    responses={401: {"model": ErrorResponse}},
)

GET_AUDIT = OpenApiParams(
    summary="Get audit",
    description="""
Retrieve an evaluation by `id`. If uncertain whether the audit is completed, or simply polling responses,
it is recommended to use [Poll audit status](/docs#tag/audit/operation/get_audit_status_audit__id__status_get)
""",
    response_model=AuditResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)

GET_AUDIT_STATUS = OpenApiParams(
    summary="Poll audit status",
    description="""
        To be used during processing. Returns the status of each AI agent used in generating results, called `steps`.
        In addition to the `steps` statuses, it will return the status of the audit as a whole. Useful in polling responses
        while waiting for processing to complete.
        """,
    response_model=GetAuditStatusResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)

SUBMIT_FEEDBACK = OpenApiParams(
    summary="Submit feedback",
    description="""
        Submit feedback for a specific finding. Only the creator of the audit can submit feedback, for now.
        `verified` represents whether the user agreed / disagreed with the findings.
        """,
    response_model=BooleanResponse,
    responses={401: {"model": ErrorResponse}},
)
