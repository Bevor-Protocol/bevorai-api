import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import Request, Response

from app.api.auth.service import AuthService
from app.api.user.service import UserService
from app.db.models import Auth, Contract, Permission
from app.utils.clients.explorer import ExplorerClient
from app.utils.schema.dependencies import AuthState
from app.utils.schema.request import ContractScanBody
from app.utils.types.enums import ClientTypeEnum, NetworkEnum, RoleEnum
from tests.constants import USER_API_KEY

USER_WITH_CREDITS_ADDRESS = "0xuserwithcredits"
USER_WITH_CREDITS_API_KEY = "user-with-credits-api-key"

# Contract addresses for testing
PROXY_TXT_ADDRESS_CLEAN = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
PROXY_JSON_ADDRESS = "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
STANDARD_JSON_ADDRESS = "0x7167cc66bE2a68553E59Af10F368056F0f6f0C69"
LARGE_JSON_ADDRESS = "0xEa19F0293453ab73214A93Fd69773684b5Eeb98f"

TEST_ADDRESSES = {
    PROXY_TXT_ADDRESS_CLEAN: {"is_proxy": True},
    PROXY_JSON_ADDRESS: {"is_proxy": True},
    STANDARD_JSON_ADDRESS: {"is_proxy": True},
    LARGE_JSON_ADDRESS: {"is_proxy": True},
}


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


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_teardown_contracts():
    """Setup and teardown for contract tests to avoid race conditions"""
    # Setup - ensure contracts don't exist before tests
    for address in TEST_ADDRESSES.keys():
        await Contract.filter(address=address).delete()

    yield

    # Teardown - clean up contracts after all tests
    for address in TEST_ADDRESSES.keys():
        await Contract.filter(address=address).delete()


@pytest.mark.anyio
async def test_contract_scan_clean(user_with_auth, async_client):
    """
    Test that the authentication dependency check works correctly for the
    sync_credits endpoint without executing the endpoint logic
    """
    # Mock the sync_credits method that will be called after dependency check
    ADDRESS = "0xfakeaddress"
    async_mock = AsyncMock()

    async def mock_get_source_code(self, client, network, address):
        request = Request("GET", "https://mocked.url")
        if network == NetworkEnum.ETH:
            return Response(
                request=request,
                status_code=200,
                content=json.dumps(
                    {"result": [{"SourceCode": "test contract content"}]}
                ),
            )
        if network == NetworkEnum.ARB:
            return Response(
                request=request,
                status_code=200,
                content=json.dumps(
                    {"result": [{"SourceCode": {"sources": {"test.sol": "some code"}}}]}
                ),
            )
        return Response(request=request, status_code=400, content=json.dumps({}))

    async_mock.side_effect = mock_get_source_code

    # Patch ExplorerClient.get_source_code
    with patch.object(ExplorerClient, "get_source_code", new=mock_get_source_code):
        mock_body = ContractScanBody(address=ADDRESS)

        response = await async_client.post(
            "/contract",
            headers={"Authorization": f"Bearer {USER_API_KEY}"},
            json=mock_body.model_dump(),
        )

        # Assertions
        assert response.status_code == 202

    mock_body = ContractScanBody(address=ADDRESS)

    response = await async_client.post(
        "/contract",
        headers={"Authorization": f"Bearer {USER_API_KEY}"},
        json=mock_body.model_dump(),
    )

    assert response.status_code == 202

    data = response.json()
    assert data["exact_match"] is True
    assert data["exists"] is True
    assert data["contract"]["network"] == NetworkEnum.ETH

    contracts = await Contract.filter(address=ADDRESS)

    assert len(contracts) == 2

    eth_contract = next(
        (contract for contract in contracts if contract.network == NetworkEnum.ETH),
        None,
    )
    arb_contract = next(
        (contract for contract in contracts if contract.network == NetworkEnum.ARB),
        None,
    )
    should_not_exist = next(
        (contract for contract in contracts if contract.network == NetworkEnum.BASE),
        None,
    )

    assert eth_contract is not None
    assert eth_contract.is_available is True
    assert eth_contract.raw_code is not None

    assert arb_contract is not None
    assert arb_contract.is_available is False

    assert should_not_exist is None

    await Contract.filter(address=ADDRESS).delete()


@pytest.mark.anyio
async def test_contract_scan_multiple_found(user_with_auth, async_client):
    """
    Test that the authentication dependency check works correctly for the
    sync_credits endpoint without executing the endpoint logic
    """
    # Mock the sync_credits method that will be called after dependency check
    ADDRESS = "0xfakeaddress"
    async_mock = AsyncMock()

    async def mock_get_source_code(self, client, network, address):
        request = Request("GET", "https://mocked.url")
        if network in [NetworkEnum.ETH, NetworkEnum.ARB]:
            return Response(
                request=request,
                status_code=200,
                content=json.dumps(
                    {"result": [{"SourceCode": "test contract content"}]}
                ),
            )
        return Response(request=request, status_code=400, content=json.dumps({}))

    async_mock.side_effect = mock_get_source_code

    # Patch ExplorerClient.get_source_code
    with patch.object(ExplorerClient, "get_source_code", new=mock_get_source_code):
        mock_body = ContractScanBody(address=ADDRESS)

        response = await async_client.post(
            "/contract",
            headers={"Authorization": f"Bearer {USER_API_KEY}"},
            json=mock_body.model_dump(),
        )

        # Assertions
        assert response.status_code == 202

    mock_body = ContractScanBody(address=ADDRESS)

    response = await async_client.post(
        "/contract",
        headers={"Authorization": f"Bearer {USER_API_KEY}"},
        json=mock_body.model_dump(),
    )

    assert response.status_code == 202

    data = response.json()
    assert data["exact_match"] is False
    assert data["exists"] is True
    assert data["contract"]["network"] in [NetworkEnum.ETH, NetworkEnum.ARB]

    contracts = await Contract.filter(address=ADDRESS)

    assert len(contracts) == 2

    for contract in contracts:
        assert contract.is_available is True
        assert contract.raw_code is not None

    non_eth_contract = next(
        (
            contract
            for contract in contracts
            if contract.network not in [NetworkEnum.ETH, NetworkEnum.ARB]
        ),
        None,
    )

    assert non_eth_contract is None

    await Contract.filter(address=ADDRESS).delete()


@pytest.mark.anyio
async def test_contract_scan_real(user_with_auth, async_client):
    for address in TEST_ADDRESSES.keys():

        contracts = await Contract.filter(address=address)
        assert len(contracts) == 0

        mock_body = ContractScanBody(address=address, network=NetworkEnum.ETH)

        response = await async_client.post(
            "/contract",
            headers={"Authorization": f"Bearer {USER_API_KEY}"},
            json=mock_body.model_dump(),
        )

        assert response.status_code == 202

        data = response.json()
        assert data["exists"] is True
        assert data["exact_match"] is True
        assert data["contract"]["network"] == NetworkEnum.ETH

        contracts = await Contract.filter(address=address)
        assert len(contracts) == 1

        eth_contract = next(
            (contract for contract in contracts if contract.network == NetworkEnum.ETH),
            None,
        )

        assert eth_contract is not None
        assert eth_contract.is_available is True
        assert eth_contract.raw_code is not None

        await Contract.filter(address=address).delete()


# @pytest.mark.anyio
# async def test_contract_ast_real(user_with_auth_and_credits, async_client):
#     for address, res in TEST_ADDRESSES.items():

#         mock_body = ContractScanBody(address=address, network=NetworkEnum.ETH)

#         response = await async_client.post(
#             "/contract/token/static",
#             headers={"Authorization": f"Bearer {USER_WITH_CREDITS_API_KEY}"},
#             json=mock_body.model_dump(),
#         )

#         assert response.status_code == 202

#         data = response.json()
#         assert StaticAnalysisTokenResult(**data)
#         result = StaticAnalysisTokenResult(**data)
#         assert result.has_proxy_functions == res["is_proxy"]
