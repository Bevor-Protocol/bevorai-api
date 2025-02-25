# flake8: noqa

from typing import Any
from uu import Error

from pydantic import BaseModel
from typing_extensions import NotRequired, TypedDict

from app.schema.contract import ContractWithCodePydantic
from app.schema.response import (
    AppInfoResponse,
    AuditResponse,
    AuditsResponse,
    CreateEvalResponse,
    GetAuditStatusResponse,
    GetCostEstimateResponse,
    IdResponse,
    StaticAnalysisTokenResult,
    UploadContractResponse,
    UserInfoResponse,
)
from app.schema.shared import BooleanResponse, ErrorResponse


class OpenApiParams(TypedDict, total=False):
    summary: NotRequired[str]
    description: NotRequired[str]
    response_model: NotRequired[type[BaseModel]]
    response_description: NotRequired[str] = "Successful Response"
    deprecated: NotRequired[bool]
    include_in_schema: NotRequired[bool]
    responses: NotRequired[dict[int | str, dict[str, Any]]]


class OpenApiSpec(TypedDict):
    get_app_info: OpenApiParams
    upsert_contract: OpenApiParams
    create_audit: OpenApiParams
    get_audits: OpenApiParams
    get_audit: OpenApiParams
    get_audit_status: OpenApiParams
    submit_feedback: OpenApiParams
    get_or_create_contract: OpenApiParams
    get_contract: OpenApiParams
    get_cost_estimate: OpenApiParams
    get_or_create_user: OpenApiParams
    get_user_info: OpenApiParams
    analyze_token: OpenApiParams


# Define OpenAPI spec as a plain dictionary (no instantiation required)
OPENAPI_SPEC: OpenApiSpec = {
    "get_app_info": {
        "summary": "Get App Info",
        "description": "Get App-level information",
        "response_model": AppInfoResponse,
        "responses": {404: {"model": ErrorResponse}},
    },
    "create_audit": {
        "summary": "Create AI eval",
        "description": """
Initializes an AI smart contract audit. `contract_id` is the referenced contract obtained
from [`POST /contract`](/docs#tag/contract/operation/upload_contract_contract__post).
`audit_type` is of type `AuditTypeEnum`.\n\n
Note, that this **consumes credits**.
        """,
        "response_model": CreateEvalResponse,
        "responses": {404: {"model": ErrorResponse}},
    },
    "get_audits": {
        "summary": "Get audits",
        "description": """
        Get audits according to a filter set. If calling as an `App`, you'll be able to view all audits generated
        through your app. If calling as a `User`, you'll be able to view your own audits (making `user_id` or `user_address` irrelevant).
        """,
        "response_model": AuditsResponse,
        "responses": {401: {"model": ErrorResponse}},
    },
    "get_audit": {
        "summary": "Get audit",
        "description": """
Retrieve an evaluation by `id`. If uncertain whether the audit is completed, or simply polling responses,
it is recommended to use [Poll audit status](/docs#tag/audit/operation/get_audit_status_audit__id__status_get)
""",
        "response_model": AuditResponse,
        "responses": {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    },
    "get_audit_status": {
        "summary": "Poll audit status",
        "description": """
        To be used during processing. Returns the status of each AI agent used in generating results, called `steps`.
        In addition to the `steps` statuses, it will return the status of the audit as a whole. Useful in polling responses
        while waiting for processing to complete.
        """,
        "response_model": GetAuditStatusResponse,
        "responses": {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    },
    "submit_feedback": {
        "summary": "Submit feedback",
        "description": """
        Submit feedback for a specific finding. Only the creator of the audit can submit feedback, for now.
        `verified` represents whether the user agreed / disagreed with the findings.
        """,
        "response_model": BooleanResponse,
        "responses": {401: {"model": ErrorResponse}},
    },
    "get_or_create_contract": {
        "summary": "Contract get/create",
        "description": """
Get or create a smart contract reference. `address` or `code` are required.
If `address` is provided, it will scan for the source code. Providing `network` will likely
speed up the response. If `code` is provided, it'll simply upload the raw code and create a reference
to it. Scanning requires that a smart contract is verified, and the source code is available. It is possible that
a given address exists on multiple chains, which is why `candidates` is provided.
        """,
        "response_model": UploadContractResponse,
        "responses": {401: {"model": ErrorResponse}},
    },
    "get_contract": {
        "summary": "Get contract by id",
        "description": "Retrieve a previously uploaded contract by `id`",
        "response_model": ContractWithCodePydantic,
        "responses": {401: {"model": ErrorResponse}},
    },
    "get_cost_estimate": {
        "summary": "Get current cost estimate",
        "description": "Can be used to infer current cost of running an eval. Response is in terms of credits.",
        "response_model": GetCostEstimateResponse,
        "responses": {401: {"model": ErrorResponse}},
    },
    "get_or_create_user": {
        "summary": "Create a user",
        "description": "Only callable from an authenticated `App`. If already exists, will return the user `id`.",
        "response_model": IdResponse,
        "responses": {401: {"model": ErrorResponse}},
    },
    "get_user_info": {
        "summary": "Get User info",
        "description": "Get stats related to a user",
        "response_model": UserInfoResponse,
        "responses": {401: {"model": ErrorResponse}},
    },
    "analyze_token": {
        "summary": "Token static analysis",
        "description": "Upload a token contract to receive a static analysis",
        "response_model": StaticAnalysisTokenResult,
        "responses": {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
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

code_example = """
### Basic Implementation

Assumes you have an API key through the BevorAI app.

```python
import requests
import time

# Upload contract
contract_response = requests.post(
    url="https://api.bevor.io/contract",
    json={
        "address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    },
    headers={
        "Authorization": f"Bearer <api-key>"
    }
)

contract_data = contract_response.json()

# Extract Contract Id
contract_id = None
network_use = "eth" # could pass this in the body, to avoid the need for "candidates"
if contract_data["exists"]:
    if contract_data["exact_match"]:
        contract_id = contract_data["candidates"][0]["id"]
    else:
        for contract in contract_data["candidates"]:
            if contract["network"] == network_use:
                contract_id = contract["id"]


# Create an Audit
audit_response = requests.post(
    url="https://api.bevor.io/audit",
    json={
        "contract_id": contract_id,
        "audit_type": "gas",
    },
    headers={
        "Authorization": f"Bearer <api-key>"
    }
)

# immediate response
audit_id = audit_response.json()["id"]


# Lightweight Poll for audit status
is_complete = False
while not is_complete:
    audit_status_response = requests.get(
        url=f"https://api.bevor.io/audit/{audit_id}/status",
        headers={
            "Authorization": f"Bearer <api-key>"
        }
    )

    audit_status_data = audit_status_response.json()
    status = audit_status_data["status"]
    if status in ["success", "failed"]:
        is_complete = True
    else:
        time.sleep(1)
        # can do something with status["steps"]

audit_response = requests.get(
    url=f"https://api.bevor.io/audit/{audit_id}",
    headers={
        "Authorization": f"Bearer <api-key>"
    }
)

audit_data = audit_response.json()

findings_json = audit_data["findings"]

print(findings_json)
```
"""


OPENAPI_SCHEMA = {
    "core": {
        "title": "BevorAI API docs",
        "version": "1.0.0",
        "summary": "**BevorAI smart contract auditor**",
        "description": _description,
        "tags": [
            {"name": "app", "description": "Relevant for `App` callers"},
            {
                "name": "audit",
                "description": "Used for creating audits",
            },
            {
                "name": "contract",
                "description": "Used for uploading, scanning, and creating smart contract references. Required for creating audits.",
            },
            {"name": "static", "description": "static analysis of smart contracts"},
            {"name": "platform"},
            {
                "name": "user",
                "description": "Creating users as an `App`, or getting user level information",
            },
            {"name": "basic implementation", "description": code_example},
        ],
    },
    # openapi extensions
    "other": {
        "x-tagGroups": [
            {"name": "Core Features", "tags": ["contract", "static", "audit"]},
            {"name": "Management", "tags": ["user", "app"]},
            {"name": "Misc", "tags": ["platform"]},
            {"name": "Examples", "tags": ["basic implementation"]},
        ],
        "info": {
            "x-logo": {
                "url": "https://app.bevor.ai/logo.png",
                "backgroundColor": "black",
            }
        },
    },
}
