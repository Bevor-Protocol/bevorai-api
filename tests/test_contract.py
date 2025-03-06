from unittest.mock import MagicMock, patch

import pytest
from httpx import Response

from app.api.blockchain.service import BlockchainService
from app.api.contract.service import ContractService
from app.db.models import Contract
from app.utils.clients.explorer import ExplorerClient
from app.utils.types.enums import ContractMethodEnum, NetworkEnum


@pytest.mark.anyio
async def test_contract_upload_clean(user_with_auth, async_client, monkeypatch):
    """
    Test that the authentication dependency check works correctly for the
    sync_credits endpoint without executing the endpoint logic
    """
    # Mock the sync_credits method that will be called after dependency check
    original_get_credits = BlockchainService.get_credits
    original_get_source_code = ExplorerClient.get_source_code

    method_called = False

    async def mock_get_source_code(self, client, network, address):
        # NOTE: we can expand this test set.
        nonlocal method_called
        method_called = True
        if network == NetworkEnum.ETH:
            return Response(
                status_code=200, json={"result": [{"SourceCode": "contract Test {}"}]}
            )
        else:
            return Response(status_code=200, json={})

    # Apply the mock to the blockchain service's get_credits method
    monkeypatch.setattr(ExplorerClient, "get_source_code", mock_get_source_code)

    monkeypatch.setattr(ExplorerClient, "get_source_code", original_get_source_code)


@pytest.mark.asyncio
async def test_fetch_from_source_with_code(test_db):
    contract_service = ContractService()

    # Test with code provided
    sample_code = "contract Test { function test() public {} }"
    response = await contract_service.fetch_from_source(code=sample_code)

    assert response.exists is True
    assert response.exact_match is True
    assert response.contract is not None
    assert response.contract.code == sample_code

    # Verify contract was created in DB
    contract = await Contract.get(id=response.contract.id)
    assert contract.raw_code == sample_code
    assert contract.method == ContractMethodEnum.UPLOAD


@pytest.mark.asyncio
async def test_fetch_from_source_with_address(test_db):
    contract_service = ContractService()

    # Create a contract first
    contract = await Contract.create(
        address="0xTEST123",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        raw_code="contract Test { function test() public {} }",
        is_available=True,
    )

    # Test fetching by address
    response = await contract_service.fetch_from_source(address="0xTEST123")

    assert response.exists is True
    assert response.contract is not None
    assert response.contract.id == str(contract.id)
    assert response.contract.address == "0xTEST123"


@pytest.mark.asyncio
async def test_get_contract(test_db):
    # Create a contract
    contract = await Contract.create(
        address="0xGET123",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        raw_code="contract Test { function get() public {} }",
        is_available=True,
    )

    contract_service = ContractService()
    response = await contract_service.get(str(contract.id))

    assert response.id == str(contract.id)
    assert response.address == "0xGET123"
    assert response.code == "contract Test { function get() public {} }"


@pytest.mark.asyncio
async def test_analyze_contract():
    contract_service = ContractService()

    # Mock AST for a simple token contract
    ast = {
        "children": [
            {
                "type": "ContractDefinition",
                "subNodes": [
                    {
                        "type": "FunctionDefinition",
                        "name": "mint",
                        "visibility": "public",
                        "body": "{ require(msg.sender == owner); _mint(to, amount); }",
                    },
                    {
                        "type": "FunctionDefinition",
                        "name": "_mint",
                        "visibility": "internal",
                        "body": "{ balances[to] += amount; }",
                    },
                ],
            }
        ]
    }

    result = contract_service.analyze_contract(ast)

    assert result.is_mintable is True
    assert result.has_allowlist is False
