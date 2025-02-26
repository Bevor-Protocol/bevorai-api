from app.db.models import Contract, Finding, IntermediateResponse, User
from app.utils.schema.audit import AuditStepPydantic, FindingPydantic
from app.utils.schema.contract import ContractPydantic, ContractWithCodePydantic
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


def cast_step(step: IntermediateResponse) -> AuditStepPydantic:
    return AuditStepPydantic(
        step=step.step,
        status=step.status,
        processing_time_seconds=step.processing_time_seconds,
    )
