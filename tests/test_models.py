from uuid import UUID

import pytest

from app.db.models import App, Audit, Contract, User
from app.utils.types.enums import (
    AppTypeEnum,
    AuditStatusEnum,
    AuditTypeEnum,
    ContractMethodEnum,
    NetworkEnum,
)


@pytest.mark.asyncio
async def test_create_user(test_db):
    user = await User.create(
        address="0x123456789abcdef",
    )
    assert user.id is not None
    assert isinstance(user.id, UUID)
    assert user.address == "0x123456789abcdef"
    assert user.total_credits == 0
    assert user.used_credits == 0

    # Verify we can retrieve the user
    retrieved = await User.get(id=user.id)
    assert retrieved.address == "0x123456789abcdef"


@pytest.mark.asyncio
async def test_create_contract(test_db):
    contract = await Contract.create(
        address="0x123456789abcdef",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        raw_code="contract Test { function test() public {} }",
    )

    assert contract.id is not None
    assert contract.address == "0x123456789abcdef"
    assert contract.network == NetworkEnum.ETH
    assert contract.method == ContractMethodEnum.SCAN
    assert contract.hash_code is not None  # Should be auto-generated

    # Test hash_code generation
    assert (
        contract.hash_code
        == "5a2adc9fb8d9e508c04e4fb17a55f8fad96a3dbb9b70b93733c60686c6c91c37"
    )


@pytest.mark.asyncio
async def test_create_app(test_db):
    user = await User.create(address="0xappowner")

    app = await App.create(owner=user, name="Test App", type=AppTypeEnum.THIRD_PARTY)

    assert app.id is not None
    assert app.name == "Test App"
    assert app.type == AppTypeEnum.THIRD_PARTY

    # Test relationship
    retrieved_app = await App.get(id=app.id).prefetch_related("owner")
    assert retrieved_app.owner.id == user.id


@pytest.mark.asyncio
async def test_create_audit(test_db):
    user = await User.create(address="0xauditor")

    contract = await Contract.create(
        address="0xcontract",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        raw_code="contract Test {}",
    )

    audit = await Audit.create(
        user=user,
        contract=contract,
        audit_type=AuditTypeEnum.SECURITY,
        status=AuditStatusEnum.WAITING,
    )

    assert audit.id is not None
    assert audit.audit_type == AuditTypeEnum.SECURITY
    assert audit.status == AuditStatusEnum.WAITING

    # Test relationships
    retrieved_audit = await Audit.get(id=audit.id).prefetch_related("user", "contract")
    assert retrieved_audit.user.id == user.id
    assert retrieved_audit.contract.id == contract.id
