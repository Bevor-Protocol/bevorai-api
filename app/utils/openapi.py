# flake8: noqa
from re import M

from pydantic import BaseModel
from typing_extensions import NotRequired, TypedDict

from app.schema.response import (
    AnalyticsResponse,
    BooleanResponse,
    CreateEvalResponse,
    GetAuditResponse,
    GetCostEstimate,
    GetEvalResponse,
    GetEvalStepsResponse,
    UploadContractResponse,
    UpsertUserResponse,
    UserInfoResponse,
)


class OpenApiParams(TypedDict, total=False):
    summary: NotRequired[str]
    description: NotRequired[str]
    response_model: NotRequired[type[BaseModel]]
    response_description: NotRequired[str] = "Successful Response"
    deprecated: NotRequired[bool]
    include_in_schema: NotRequired[bool]


class OpenApiSpec(TypedDict):
    upsert_contract: OpenApiParams
    start_eval: OpenApiParams
    get_eval: OpenApiParams
    get_eval_steps: OpenApiParams
    cost_estimate: OpenApiParams
    get_audits: OpenApiParams
    get_audit: OpenApiParams
    submit_feedback: OpenApiParams
    upsert_user: OpenApiParams


# Define OpenAPI spec as a plain dictionary (no instantiation required)
OPENAPI_SPEC: OpenApiSpec = {
    "upsert_contract": {
        "summary": "Contract scan/upload",
        "description": """
        Get or create a smart contract reference. `address` or `code` are required.
        If `network` is provided, it will likely speed up the response. Scanning requires
        that a smart contract is verified, and the source code is available. It is possible that
        a given address exists on multiple chains, which is why `candidates` is provided.
        """,
        "response_model": UploadContractResponse,
    },
    "start_eval": {
        "summary": "Create AI eval",
        "description": """
        Initializes an AI smart contract audit. `contract_id` is the referenced contract obtained
        from [`/blockchain/contract`](/redoc#tag/blockchain/operation/upload_contract_blockchain_contract_post).
        `audit_type` is of type `AuditTypeEnum`.\n\n
        Note, that this **consumes credits**.
        """,
        "response_model": CreateEvalResponse,
    },
    "get_eval": {
        "summary": "Get an AI evaluation",
        "description": "Retrieve an evaluation by `id`. Response type is determined by `response_type`",
        "response_model": GetEvalResponse,
    },
    "get_eval_steps": {
        "summary": "Get status of each expert",
        "description": """
        To be used during processing. Returns the status of each AI agent used to generate results, called `steps`.
        In addition to the `steps` statuses, it will return the status of the audit as a whole. Useful in polling responses
        while waiting for processing to complete.
        """,
        "response_model": GetEvalStepsResponse,
    },
    "cost_estimate": {
        "summary": "Get current cost estimate",
        "description": "Can be used to infer current cost of running an eval. Response is in terms of credits.",
        "response_model": GetCostEstimate,
    },
    "get_audits": {
        "summary": "Get audits",
        "description": """
        Get audits according to a filter set. If calling as an `App`, you'll be able to view all audits generated
        through your app. If calling as a `User`, you'll be able to view your own audits (making `user_id` or `user_address` irrelevant).
        """,
        "response_model": AnalyticsResponse,
    },
    "get_audit": {
        "summary": "Get an AI evaluation, granular",
        "description": "Retrieve an evaluation by `id`. Slightly more granular info than [`/eval/{id}`](/redoc#tag/ai/operation/get_eval_by_id_ai_eval__id__get)",
        "response_model": GetAuditResponse,
    },
    "submit_feedback": {
        "summary": "Submit feedback",
        "description": """
        Submit feedback for a specific finding. Only the creator of the audit can submit feedback, for now.
        `verified` represents whether the user agreed / disagreed with the findings.
        """,
        "response_model": BooleanResponse,
    },
    "upsert_user": {
        "summary": "Upsert a user",
        "description": "Only callable from an authenticated `App`",
        "response_model": UpsertUserResponse,
    },
}

_description = """
We're in private Beta. Reach out to our team if you'd like access. Once granted access, 
go to <a href='https://app.bevor.ai/dashboard' target='_blank'>BevorAI App</a> to create your API key.

### Authentication
There are **2 roles** that you can create authentication for:
- `User`
- `App`

The `App` role is a superset of the `User` role. It allows you to create users, and make requests on behalf
of other users. This is useful if you'd like to natively distinguish requests across users on your application.
If you do not need this capability, it's recommended to authenticate as a `User`.

*Note: the `x-user-identifier` header can be ignored if making requests as a `User`*

### Contracts
You can scan contracts, OR upload raw smart contract code.

### AI Eval
BevorAI will conduct its smart contract security audit given the Contract instance, and the type of
audit you'd like. We support `security` and `gas optimization` audits.
Completions generally takes 30-60s.
"""


OPENAPI_SCHEMA = {
    "title": "BevorAI API docs",
    "version": "1.0.0",
    "summary": "**BevorAI smart contract auditor**",
    "description": _description,
    "tags": [
        {
            "name": "blockchain",
            "description": "Operations interacting with on-chain data",
        },
        {
            "name": "ai",
            "description": "Core of the API. Used to create evaluations, get responses, and poll the API",
        },
        {"name": "auth", "description": "Relevant for `App` callers"},
    ],
}
