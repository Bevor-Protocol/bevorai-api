# flake8: noqa

# Define OpenAPI spec as a plain dictionary (no instantiation required)

from app.utils.constants.openapi_tags import (
    APP_TAG,
    AUDIT_TAG,
    CODE_EXAMPLE_TAG,
    CONTRACT_TAG,
    PLATFORM_TAG,
    TAG_GROUP_CORE,
    TAG_GROUP_EXAMPLES,
    TAG_GROUP_MANAGEMENT,
    TAG_GROUP_MISC,
    USER_TAG,
)

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

*Note: the `Bevor-User-Identifier` header can be ignored if making requests as a `User`*

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
            {"name": APP_TAG, "description": "Relevant for `App` callers"},
            {
                "name": AUDIT_TAG,
                "description": "Used for creating audits",
            },
            {
                "name": CONTRACT_TAG,
                "description": "Used for uploading, scanning, and creating smart contract references. Required for creating audits.",
            },
            {"name": PLATFORM_TAG},
            {
                "name": USER_TAG,
                "description": "Creating users as an `App`, or getting user level information",
            },
            {"name": CODE_EXAMPLE_TAG, "description": code_example},
        ],
    },
    # openapi extensions
    "other": {
        "x-tagGroups": [
            {"name": TAG_GROUP_CORE, "tags": [CONTRACT_TAG, AUDIT_TAG]},
            {"name": TAG_GROUP_MANAGEMENT, "tags": [USER_TAG, APP_TAG]},
            {"name": TAG_GROUP_MISC, "tags": [PLATFORM_TAG]},
            {"name": TAG_GROUP_EXAMPLES, "tags": [CODE_EXAMPLE_TAG]},
        ],
        "info": {
            "x-logo": {
                "url": "https://app.bevor.ai/logo.png",
                "backgroundColor": "black",
            }
        },
    },
}
