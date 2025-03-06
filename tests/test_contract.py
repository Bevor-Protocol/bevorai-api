from unittest.mock import MagicMock, patch

import pytest

from app.api.contract.service import ContractService
from app.db.models import Contract
from app.utils.types.enums import ContractMethodEnum, NetworkEnum


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
