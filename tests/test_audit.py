import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.api.audit.interface import CreateEvalResponse, EvalBody
from app.api.audit.service import AuditService
from app.api.auth.service import AuthService
from app.api.pipeline.types import (
    GasOutputStructure,
    GasFindingsStructure,
    GasFindingType,
)
from app.api.user.service import UserService
from app.db.models import (
    Audit,
    AuditMetadata,
    Auth,
    Contract,
    Finding,
    IntermediateResponse,
    Permission,
    Prompt,
    User,
)
from app.utils.types.shared import AuthState
from app.utils.types.enums import (
    AuditStatusEnum,
    AuditTypeEnum,
    ClientTypeEnum,
    ContractMethodEnum,
    FindingLevelEnum,
    NetworkEnum,
    RoleEnum,
)
from tests.constants import THIRD_PARTY_APP_API_KEY, USER_API_KEY

USER_WITH_CREDITS_ADDRESS = "0xuserwithcredits"
USER_WITH_CREDITS_API_KEY = "user-with-credits-api-key"


@pytest_asyncio.fixture(scope="module")
async def user_with_auth_and_credits():
    """Create a user who requested an API key"""
    user_service = UserService()
    auth_service = AuthService()

    user = await user_service.get_or_create(USER_WITH_CREDITS_ADDRESS)
    user.total_credits = 100.0
    await user.save()
    permissions = await Permission.get(user_id=user.id)

    # currently done manually.
    permissions.can_create_api_key = True
    permissions.can_create_app = True

    await permissions.save()

    mock_auth_state = AuthState(
        user_id=user.id,
        consumes_credits=True,
        credit_consumer_user_id=user.id,
        role=RoleEnum.USER,
    )

    intermediate_key = await auth_service.generate(
        auth_obj=mock_auth_state, client_type=ClientTypeEnum.USER
    )

    assert len(intermediate_key)

    # can't pass key to service. explicitly update it to known value.
    hashed_key = Auth.hash_key(USER_WITH_CREDITS_API_KEY)
    auth = await Auth.get(user_id=user.id)
    auth.hashed_key = hashed_key
    await auth.save()

    return user


@pytest_asyncio.fixture(scope="module")
async def mock_prompts():
    await Prompt.create(
        audit_type=AuditTypeEnum.GAS, tag="test-1", version="0.1", content="fake prompt"
    )
    await Prompt.create(
        audit_type=AuditTypeEnum.GAS, tag="test-2", version="0.1", content="fake prompt"
    )
    await Prompt.create(
        audit_type=AuditTypeEnum.GAS,
        tag="reviewer",
        version="0.1",
        content="fake prompt",
    )
    await Prompt.create(
        audit_type=AuditTypeEnum.SECURITY,
        tag="test-1",
        version="0.1",
        content="fake prompt",
    )
    await Prompt.create(
        audit_type=AuditTypeEnum.SECURITY,
        tag="test-2",
        version="0.1",
        content="fake prompt",
    )
    await Prompt.create(
        audit_type=AuditTypeEnum.SECURITY,
        tag="reviewer",
        version="0.1",
        content="fake prompt",
    )


@pytest.mark.anyio
async def test_fail_if_no_credits(user_with_auth, async_client):
    assert user_with_auth.total_credits == 0

    mock_body = EvalBody(contract_id="some-fake-id", audit_type=AuditTypeEnum.SECURITY)

    # Make request to create an audit
    response = await async_client.post(
        "/audit",
        headers={"Authorization": f"Bearer {USER_API_KEY}"},
        json=mock_body.model_dump(),
    )

    assert response.status_code == 402


@pytest.mark.anyio
async def test_succeed_if_credits(user_with_auth_and_credits, async_client):
    assert user_with_auth_and_credits.total_credits > 0

    mock_body = EvalBody(contract_id="some-fake-id", audit_type=AuditTypeEnum.SECURITY)

    with patch.object(AuditService, "initiate_audit") as mock_process:
        # Setup mock return value
        mock_audit_id = "test-audit-id"
        mock_status = AuditStatusEnum.WAITING

        mock_response = CreateEvalResponse(id=mock_audit_id, status=mock_status)
        mock_process.return_value = mock_response

        # Make request to create an audit
        response = await async_client.post(
            "/audit",
            headers={"Authorization": f"Bearer {USER_WITH_CREDITS_API_KEY}"},
            json=mock_body.model_dump(),
        )

        # Assertions
        assert response.status_code == 201
        mock_process.assert_called_once()
        data = response.json()
        assert data == mock_response.model_dump()


@pytest.mark.anyio
async def test_fail_if_no_contract(user_with_auth_and_credits, async_client):
    mock_body = EvalBody(contract_id="some-fake-id", audit_type=AuditTypeEnum.SECURITY)

    # Make request to create an audit
    response = await async_client.post(
        "/audit",
        headers={"Authorization": f"Bearer {USER_WITH_CREDITS_API_KEY}"},
        json=mock_body.model_dump(),
    )

    # Assertions
    assert response.status_code == 404


@pytest.mark.anyio
async def test_fail_if_invalid_body(user_with_auth_and_credits, async_client):
    # Make request to create an audit
    response = await async_client.post(
        "/audit",
        headers={"Authorization": f"Bearer {USER_WITH_CREDITS_API_KEY}"},
        json={
            "contract_id": "test",
            "audit_type": "i-dont-exist-as-a-type",
        },
    )

    # Assertion of inprocessable entity (fails in fastapi body parsing)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_successfully_creates_audit(user_with_auth_and_credits, async_client):
    assert user_with_auth_and_credits.total_credits > 0

    # Create a contract for testing
    contract = await Contract.create(
        address="0xTESTCONTRACT",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        code="contract Test {}",
        is_available=True,
    )

    mock_body = EvalBody(
        contract_id=str(contract.id), audit_type=AuditTypeEnum.SECURITY
    )
    mock_trace_context = {"traceparent": "mocked-traceparent-value-00-1234"}

    # Mock the redis pool to avoid actual job enqueuing
    with (
        patch("app.api.audit.service.create_pool") as mock_create_pool,
        patch("app.api.audit.service.get_context", return_value=mock_trace_context),
    ):
        mock_redis_pool = MagicMock()
        mock_redis_pool.enqueue_job = AsyncMock()
        mock_create_pool.return_value = mock_redis_pool

        # Make request to create an audit
        response = await async_client.post(
            "/audit",
            headers={"Authorization": f"Bearer {USER_WITH_CREDITS_API_KEY}"},
            json=mock_body.model_dump(),
        )

        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == AuditStatusEnum.WAITING.value

        # Verify redis job was enqueued
        mock_redis_pool.enqueue_job.assert_called_once_with(
            "process_eval", _job_id=data["id"], trace=mock_trace_context
        )

        # Verify audit was created in database
        audit = await Audit.get(id=data["id"])
        assert audit.contract_id == contract.id
        assert audit.audit_type == AuditTypeEnum.SECURITY

    # Clean up
    await contract.delete()
    await audit.delete()


class MockQueue:
    def __init__(self):
        self.job = None

    async def enqueue_job(self, function: str, _job_id: str, trace: None, *args):
        self.job = {"job_id": _job_id, "function": function, "trace": trace}


@pytest.mark.anyio
async def test_audit_processing_with_intermediate_states(
    user_with_auth_and_credits, async_client, mock_prompts
):
    """This is intentionally a very large e2e test with the worker"""
    assert user_with_auth_and_credits.total_credits > 0

    # Create a contract for testing
    contract = await Contract.create(
        address="0xARQTESTCONTRACT",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        code="contract ArqTest {}",
        is_available=True,
    )

    audit = await Audit.create(
        contract_id=contract.id,
        user_id=user_with_auth_and_credits.id,
        status=AuditStatusEnum.WAITING,
        audit_type=AuditTypeEnum.GAS,
    )

    mock_body = EvalBody(contract_id=str(contract.id), audit_type=AuditTypeEnum.GAS)

    from app.worker.main import process_eval

    # Mock the arq Redis pool creation
    with patch("app.api.audit.service.create_pool") as mock_create_pool:
        mock_redis_pool = MockQueue()
        mock_create_pool.return_value = mock_redis_pool

        # Make request to create an audit
        response = await async_client.post(
            "/audit",
            headers={"Authorization": f"Bearer {USER_WITH_CREDITS_API_KEY}"},
            json=mock_body.model_dump(),
        )

        # Assertions for response
        assert response.status_code == 201
        data = response.json()

        audit_id = data["id"]

        assert mock_redis_pool.job is not None

        job = mock_redis_pool.job

        # Verify job was enqueued with correct parameters
        audit_id_job = job["job_id"]
        assert audit_id == audit_id_job

        mock_structure = GasOutputStructure(
            introduction="test intro",
            scope="mock scope",
            conclusion="mock conclusion",
            findings=GasFindingsStructure(
                critical=[
                    GasFindingType(
                        name="fake name",
                        explanation="fake exp",
                        recommendation="fake ex",
                        reference="fake ref",
                    )
                ],
                high=[],
                medium=[],
                low=[
                    GasFindingType(
                        name="fake name",
                        explanation="fake exp",
                        recommendation="fake ex",
                        reference="fake ref",
                    )
                ],
            ),
        )

        mock_str = json.dumps(mock_structure.model_dump())

        # Create mock methods that check state before and after
        # Counter to track number of calls to mock_chat_completions_create
        # Use a thread-safe counter for async calls
        inter_responses = []

        # Use a shared set to track which calls have failed
        failed_calls = set()

        async def mock_chat_completions_create(*args, **kwargs):
            # intermediate state would've been created already, in processing.
            last_added = await IntermediateResponse.filter(audit_id=audit_id)
            assert last_added[0].status == AuditStatusEnum.PROCESSING

            # Get the current intermediate response ID
            current_id = last_added[0].id
            inter_responses.append(current_id)

            # Fail exactly one call based on the ID
            # This ensures deterministic failure even with async execution
            if current_id not in failed_calls and not failed_calls:
                failed_calls.add(current_id)
                raise Exception("Simulated error in llm request")

            # Return mock response for other calls
            mock_response = AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content="Mock LLM response"))],
                usage=AsyncMock(prompt_tokens=100, completion_tokens=100),
            )

            return mock_response

        async def mock_chat_completions_parse(*args, **kwargs):
            # audit should still be processing
            audit_before = await Audit.get(id=audit_id)
            assert audit_before.status == AuditStatusEnum.PROCESSING

            # Return mock response with the structure needed
            return AsyncMock(
                choices=[AsyncMock(message=AsyncMock(content=mock_str))],
                usage=AsyncMock(prompt_tokens=500, completion_tokens=500),
            )

        mock_trace_context = {"traceparent": "mocked-traceparent-value-00-1234"}

        # # Mock the LLM client methods
        with patch("app.api.pipeline.audit_generation.llm_client") as mock_llm_client:
            # Configure the mock methods
            mock_llm_client.chat.completions.create = mock_chat_completions_create
            mock_llm_client.beta.chat.completions.parse = mock_chat_completions_parse

            # Process the evaluation
            await process_eval(job, mock_trace_context)

    # Verify the audit status changes
    updated_audit = await Audit.get(id=audit_id)
    assert updated_audit.audit_type == AuditTypeEnum.GAS
    assert updated_audit.contract_id == contract.id
    assert updated_audit.status == AuditStatusEnum.SUCCESS
    assert updated_audit.processing_time_seconds is not None

    audit_metadata = await AuditMetadata.get(audit_id=audit_id)
    assert audit_metadata.introduction == "test intro"
    assert audit_metadata.scope == "mock scope"
    assert audit_metadata.conclusion == "mock conclusion"

    inter_responses_db = await IntermediateResponse.filter(audit_id=audit_id)
    assert (
        next(
            filter(lambda x: x.status == AuditStatusEnum.FAILED, inter_responses_db),
            None,
        )
        is not None
    )

    findings = await Finding.filter(audit_id=audit_id)
    assert len(findings) == 2  # as denoted by the mock_structure

    user = await User.get(id=user_with_auth_and_credits.id)
    assert user.total_credits > 0
    assert user.used_credits > 0

    # Clean up
    await audit.delete()
    await audit_metadata.delete()
    await contract.delete()

    # reset fixture state.
    user_with_auth_and_credits.total_credits = 100
    user_with_auth_and_credits.used_credits = 0
    await user_with_auth_and_credits.save()


@pytest.mark.anyio
async def test_get_audit(user_with_auth, async_client):
    """Test retrieving a specific audit through the API endpoint"""
    # Create test data
    user = await User.get(id=user_with_auth.id)
    contract = await Contract.create(
        address="0xAUDITGET",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        code="contract Test {}",
    )

    audit = await Audit.create(
        user=user,
        contract=contract,
        audit_type=AuditTypeEnum.SECURITY,
        status=AuditStatusEnum.SUCCESS,
    )

    audit_metadata = await AuditMetadata.create(
        audit=audit, introduction="Test", scope="Test", conclusion="Test"
    )

    # Make request to get the audit
    response = await async_client.get(
        f"/audit/{audit.id}",
        headers={"Authorization": f"Bearer {USER_API_KEY}"},
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(audit.id)
    assert data["audit_type"] == AuditTypeEnum.SECURITY.value
    assert data["status"] == AuditStatusEnum.SUCCESS.value
    assert data["contract"]["id"] == str(contract.id)
    assert data["user"]["id"] == str(user.id)

    # Clean up
    await audit_metadata.delete()
    await audit.delete()
    await contract.delete()


@pytest.mark.anyio
async def test_get_audits(user_with_auth, async_client):
    """Test retrieving a list of audits through the API endpoint"""
    # Create test data
    contract = await Contract.create(
        address="0xAUDITLIST",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        code="contract Test {}",
    )

    # Create multiple audits
    audit1 = await Audit.create(
        user=user_with_auth,
        contract=contract,
        audit_type=AuditTypeEnum.SECURITY,
        status=AuditStatusEnum.SUCCESS,
    )
    audit_metadata1 = await AuditMetadata.create(
        audit=audit1, introduction="Test", scope="Test", conclusion="Test"
    )

    audit2 = await Audit.create(
        user=user_with_auth,
        contract=contract,
        audit_type=AuditTypeEnum.GAS,
        status=AuditStatusEnum.SUCCESS,
    )
    audit_metadata2 = await AuditMetadata.create(
        audit=audit2, introduction="Test", scope="Test", conclusion="Test"
    )

    # Make request to get audits
    response = await async_client.get(
        "/audit/list",
        headers={"Authorization": f"Bearer {USER_API_KEY}"},
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) >= 2  # At least our 2 audits

    # Verify our created audits are in the results
    audit_ids = [a["id"] for a in data["results"]]
    assert str(audit1.id) in audit_ids
    assert str(audit2.id) in audit_ids

    # Test filtering by audit type
    response = await async_client.get(
        f"/audit/list?audit_type={AuditTypeEnum.SECURITY.value}&network={NetworkEnum.ETH.value}",  # noqa
        headers={"Authorization": f"Bearer {USER_API_KEY}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1

    # Clean up
    await audit_metadata1.delete()
    await audit_metadata2.delete()
    await audit1.delete()
    await audit2.delete()
    await contract.delete()


@pytest.mark.anyio
async def test_submit_feedback(user_with_auth, async_client):
    """Test submitting feedback for a finding through the API endpoint"""
    # Create test data
    contract = await Contract.create(
        address="0xAUDITFEEDBACK",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        code="contract Test {}",
    )

    audit = await Audit.create(
        user=user_with_auth,
        contract=contract,
        audit_type=AuditTypeEnum.SECURITY,
        status=AuditStatusEnum.SUCCESS,
    )

    # Create a finding
    finding = await Finding.create(
        audit=audit,
        audit_type=AuditTypeEnum.SECURITY,
        level=FindingLevelEnum.HIGH,
        name="Test Finding",
        explanation="Test explanation",
        recommendation="Test recommendation",
    )

    # Make request to submit feedback
    feedback_data = {
        "verified": True,
        "feedback": "Good finding",
    }

    response = await async_client.post(
        f"/audit/{finding.id}/feedback",
        headers={"Authorization": f"Bearer {USER_API_KEY}"},
        json=feedback_data,
    )

    # Assertions
    assert response.status_code == 201

    # Verify finding was updated
    updated_finding = await Finding.get(id=finding.id)
    assert updated_finding.is_attested is True
    assert updated_finding.is_verified is True
    assert updated_finding.feedback == "Good finding"

    # Clean up
    await finding.delete()
    await audit.delete()
    await contract.delete()


@pytest.mark.anyio
async def test_get_audit_with_delegation(user_with_auth, third_party_app, async_client):
    """Test retrieving a specific audit through the API endpoint"""
    # Create test data
    contract = await Contract.create(
        address="0xAUDITGET",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        code="contract Test {}",
    )

    audit = await Audit.create(
        user=user_with_auth,
        contract=contract,
        audit_type=AuditTypeEnum.SECURITY,
        status=AuditStatusEnum.SUCCESS,
    )

    # Make request to get the audit
    response = await async_client.get(
        f"/audit/{audit.id}",
        headers={"Authorization": f"Bearer {THIRD_PARTY_APP_API_KEY}"},
    )

    # Assertions
    assert response.status_code == 404
    await audit.delete()

    audit = await Audit.create(
        app=third_party_app,
        user=user_with_auth,
        contract=contract,
        audit_type=AuditTypeEnum.SECURITY,
        status=AuditStatusEnum.SUCCESS,
    )

    response = await async_client.get(
        f"/audit/{audit.id}",
        headers={"Authorization": f"Bearer {THIRD_PARTY_APP_API_KEY}"},
    )
    assert response.status_code == 200

    # Clean up
    await audit.delete()
    await contract.delete()
