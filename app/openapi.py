# flake8: noqa

# Define OpenAPI spec as a plain dictionary (no instantiation required)

from fastapi import FastAPI
from app.utils.openapi_tags import (
    APP_TAG,
    AUDIT_TAG,
    CODE_EXAMPLE_APP_TAG,
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
        "network": "eth", # optional
    },
    headers={
        "Authorization": f"Bearer <api-key>"
    }
)

contract_data = contract_response.json()

# Extract Contract Id
contract_id = None
if contract_data["exists"]:
    contract_id = contract_data["contract"]["id"]

# if contract_id is None, it means that there was no verified source code (if requested via scan)
# or something else went wrong.
# if contract_data["exact_match"] is false, it means that `network` was not provided in the request
# and multiple instances of this address were found across different networks.


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

code_app_example = """
### Basic Implementation as an App

Assumes you have an App and an API key for your App through the BevorAI app.
While you can authenticate only on behalf of your App, you can also delegate certain
responses via the Bevor-User-Identifier header, to natively be able to differentiate
users in your application.

```python
import requests
import time

# Get or create a User
user_response = requests.post(
    url="https://api.bevor.io",
    headers={
        "Authorization": f"Bearer <api-key>"
    }
    json={
        "address": <user-wallet-address>,
    }
)

user_data = user_response.json()
user_id = user_data["id"]

# Upload contract
contract_response = requests.post(
    url="https://api.bevor.io/contract",
    json={
        "address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "network": "eth", # optional
    },
    headers={
        "Authorization": f"Bearer <api-key>"
        # using Bevor-User-Identifier has no impact here
    }
)

contract_data = contract_response.json()

# Extract Contract Id
contract_id = None
if contract_data["exists"]:
    contract_id = contract_data["contract"]["id"]


# Create an Audit

# declare that the audit was created on behalf of a User
# if the Bevor-User-Identifier header is excluded, the audit will be created on
# behalf of your App

audit_response = requests.post(
    url="https://api.bevor.io/audit",
    json={
        "contract_id": contract_id,
        "audit_type": "gas",
    },
    headers={
        "Authorization": f"Bearer <api-key>"
        "Bevor-User-Identifier": user_id
    }
)

# immediate response
audit_id = audit_response.json()["id"]

# When querying for the audit, you must include the same Bevor-User-Identifier that you used to create the audit.
# if you excluded the header in the audit creation, you can exclude it in the audit queries as well.


# Lightweight Poll for audit status
is_complete = False
while not is_complete:
    audit_status_response = requests.get(
        url=f"https://api.bevor.io/audit/{audit_id}/status",
        headers={
            "Authorization": f"Bearer <api-key>",
            "Bevor-User-Identifier": user_id
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
        "Authorization": f"Bearer <api-key>",
        "Bevor-User-Identifier": user_id
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
            {"name": CODE_EXAMPLE_APP_TAG, "description": code_app_example},
        ],
    },
    # openapi extensions
    "other": {
        "x-tagGroups": [
            {"name": TAG_GROUP_CORE, "tags": [CONTRACT_TAG, AUDIT_TAG]},
            {"name": TAG_GROUP_MANAGEMENT, "tags": [USER_TAG, APP_TAG]},
            {"name": TAG_GROUP_MISC, "tags": [PLATFORM_TAG]},
            {
                "name": TAG_GROUP_EXAMPLES,
                "tags": [CODE_EXAMPLE_TAG, CODE_EXAMPLE_APP_TAG],
            },
        ],
        "info": {
            "x-logo": {
                "url": "https://app.bevor.ai/logo.png",
                "backgroundColor": "black",
            }
        },
    },
}


def customize_openapi(app: FastAPI):
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        **OPENAPI_SCHEMA["core"],
        routes=app.routes,
    )

    for k, v in OPENAPI_SCHEMA["other"].items():
        if isinstance(v, dict):
            openapi_schema.setdefault(k, {}).update(v)
        elif isinstance(v, list):
            openapi_schema.setdefault(k, []).extend(v)
        else:
            openapi_schema[k] = v
    app.openapi_schema = openapi_schema
    return app.openapi_schema
