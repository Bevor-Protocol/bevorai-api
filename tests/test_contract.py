import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Request, Response

from app.db.models import Contract
from app.utils.clients.explorer import ExplorerClient
from app.utils.schema.request import ContractScanBody
from app.utils.types.enums import NetworkEnum
from tests.constants import USER_API_KEY


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
        return Response(request=request, status_code=200, content=json.dumps({}))

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

    assert len(contracts) > 0

    eth_contract = next(
        (contract for contract in contracts if contract.network == NetworkEnum.ETH),
        None,
    )
    non_eth_contract = next(
        (contract for contract in contracts if contract.network != NetworkEnum.ETH),
        None,
    )
    assert eth_contract is not None
    assert eth_contract.is_available is True
    assert eth_contract.raw_code is not None
    assert non_eth_contract.is_available is False
    assert non_eth_contract.raw_code is None

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
        return Response(request=request, status_code=200, content=json.dumps({}))

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

    assert len(contracts) > 0

    eth_contract = next(
        (
            contract
            for contract in contracts
            if contract.network in [NetworkEnum.ETH, NetworkEnum.ARB]
        ),
        None,
    )
    non_eth_contract = next(
        (
            contract
            for contract in contracts
            if contract.network not in [NetworkEnum.ETH, NetworkEnum.ARB]
        ),
        None,
    )
    assert eth_contract is not None
    assert eth_contract.is_available is True
    assert eth_contract.raw_code is not None
    assert non_eth_contract.is_available is False
    assert non_eth_contract.raw_code is None

    await Contract.filter(address=ADDRESS).delete()


# TODO: create test for the json return type from etherscan...


# TODO: write test for AST + parser
