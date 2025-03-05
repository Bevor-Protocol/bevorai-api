import json

import pytest

from app.api.audit.service import AuditService
from app.db.models import Audit, Contract, Finding, User
from app.utils.schema.dependencies import AuthState
from app.utils.schema.request import FilterParams
from app.utils.types.enums import (
    AuditStatusEnum,
    AuditTypeEnum,
    ContractMethodEnum,
    FindingLevelEnum,
    NetworkEnum,
    RoleEnum,
)


@pytest.fixture
async def setup_audit_data(test_db):
    user = await User.create(address="0xAUDITOR")

    contract = await Contract.create(
        address="0xCONTRACT",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        raw_code="contract Test {}",
    )

    output_json = {
        "introduction": "Test",
        "scope": "Test",
        "conclusion": "Test",
        "findings": {
            FindingLevelEnum.CRITICAL.value: [],
            FindingLevelEnum.HIGH.value: [],
            FindingLevelEnum.MEDIUM.value: [],
            FindingLevelEnum.LOW.value: [],
        },
    }

    audit = await Audit.create(
        user=user,
        contract=contract,
        audit_type=AuditTypeEnum.SECURITY,
        status=AuditStatusEnum.SUCCESS,
        raw_output=json.loads(output_json),
    )

    return {"user": user, "contract": contract, "audit": audit}


@pytest.mark.asyncio
async def test_get_audits(setup_audit_data):
    # Await the fixture to get the actual data
    data = setup_audit_data

    audit_service = AuditService()

    # Test as user
    auth_state = AuthState(
        role=RoleEnum.USER,
        user_id=str(data["user"].id),
        app_id=None,
        is_delegated=False,
        consumes_credits=True,
        credit_consumer_user_id=str(data["user"].id),
    )

    query = FilterParams()
    response = await audit_service.get_audits(auth=auth_state, query=query)

    assert len(response.results) == 1
    assert response.results[0].id == str(data["audit"].id)
    assert response.results[0].audit_type == AuditTypeEnum.SECURITY
    assert response.results[0].status == AuditStatusEnum.SUCCESS


@pytest.mark.asyncio
async def test_get_audit(setup_audit_data):
    # Await the fixture to get the actual data
    data = await setup_audit_data

    audit_service = AuditService()

    # Test as user
    auth_state = AuthState(
        role=RoleEnum.USER,
        user_id=str(data["user"].id),
        app_id=None,
        is_delegated=False,
        consumes_credits=True,
        credit_consumer_user_id=str(data["user"].id),
    )

    response = await audit_service.get_audit(auth=auth_state, id=str(data["audit"].id))

    assert response.id == str(data["audit"].id)
    assert response.audit_type == AuditTypeEnum.SECURITY
    assert response.status == AuditStatusEnum.SUCCESS
    assert response.contract.id == str(data["contract"].id)
    assert response.user.id == str(data["user"].id)


@pytest.mark.asyncio
async def test_submit_feedback(setup_audit_data):
    # Await the fixture to get the actual data
    data = await setup_audit_data

    # Create a finding
    finding = await Finding.create(
        audit=data["audit"],
        audit_type=AuditTypeEnum.SECURITY,
        level=FindingLevelEnum.HIGH,
        name="Test Finding",
        explanation="Test explanation",
        recommendation="Test recommendation",
    )

    audit_service = AuditService()

    # Test as user
    auth_state = AuthState(
        role=RoleEnum.USER,
        user_id=str(data["user"].id),
        app_id=None,
        is_delegated=False,
        consumes_credits=True,
        credit_consumer_user_id=str(data["user"].id),
    )

    from app.utils.schema.request import FeedbackBody

    feedback = FeedbackBody(verified=True, feedback="Good finding")

    result = await audit_service.submit_feedback(
        data=feedback, auth=auth_state, id=str(finding.id)
    )

    assert result is True

    # Verify finding was updated
    updated_finding = await Finding.get(id=finding.id)
    assert updated_finding.is_attested is True
    assert updated_finding.is_verified is True
    assert updated_finding.feedback == "Good finding"
