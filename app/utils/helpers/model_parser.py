from app.db.models import (
    App,
    Contract,
    Finding,
    IntermediateResponse,
    Permission,
    Prompt,
    User,
)
from app.utils.schema.app import AppPydantic
from app.utils.schema.audit import AuditStepPydantic, FindingPydantic
from app.utils.schema.contract import ContractPydantic, ContractWithCodePydantic
from app.utils.schema.permission import PermissionPydantic
from app.utils.schema.prompt import PromptPydantic
from app.utils.schema.user import UserPydantic

"""
Used to convert tortoise ORM models into pydantic models, with baked
in serialization
"""


def cast_finding(finding: Finding) -> FindingPydantic:
    return FindingPydantic(
        id=finding.id,
        level=finding.level,
        name=finding.name,
        explanation=finding.explanation,
        recommendation=finding.recommendation,
        reference=finding.reference,
        is_attested=finding.is_attested,
        is_verified=finding.is_verified,
        feedback=finding.feedback,
    )


def cast_contract(contract: Contract) -> ContractPydantic:
    return ContractPydantic(
        id=contract.id,
        method=contract.method,
        address=contract.address,
        network=contract.network,
        is_available=contract.is_available,
    )


def cast_contract_with_code(contract: Contract) -> ContractWithCodePydantic:
    return ContractWithCodePydantic(
        id=contract.id,
        method=contract.method,
        address=contract.address,
        network=contract.network,
        is_available=contract.is_available,
        code=contract.raw_code,
    )


def cast_user(user: User) -> UserPydantic:
    return UserPydantic(id=user.id, address=user.address)


def cast_app(app: App) -> AppPydantic:
    return AppPydantic(id=app.id, owner_id=app.owner_id, name=app.name, type=app.type)


def cast_step(step: IntermediateResponse) -> AuditStepPydantic:
    return AuditStepPydantic(
        step=step.step,
        status=step.status,
        processing_time_seconds=step.processing_time_seconds,
    )


def cast_permission(permission: Permission) -> PermissionPydantic:
    return PermissionPydantic(
        app_id=permission.app_id,
        user_id=permission.user_id,
        client_type=permission.client_type,
        can_create_app=permission.can_create_app,
        can_create_api_key=permission.can_create_api_key,
    )


def cast_prompt(prompt: Prompt) -> PromptPydantic:
    return PromptPydantic(
        id=prompt.id,
        created_at=prompt.created_at,
        audit_type=prompt.audit_type,
        is_active=prompt.is_active,
        tag=prompt.tag,
        version=prompt.version,
        content=prompt.content,
    )
