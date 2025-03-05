import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.models import Auth, Contract, User
from app.main import app
from app.utils.types.enums import (
    AuditTypeEnum,
    ClientTypeEnum,
    ContractMethodEnum,
    NetworkEnum,
)

client = TestClient(app)


@pytest.fixture
async def setup_auth_data(test_db):
    # Create a user
    user = await User.create(address="0xTESTUSER")

    # Create an API key
    api_key, hashed_key = Auth.create_credentials()
    auth = await Auth.create(
        user=user, client_type=ClientTypeEnum.USER, hashed_key=hashed_key
    )

    # Create a contract
    contract = await Contract.create(
        address="0xTESTCONTRACT",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        raw_code="contract Test {}",
    )

    return {"user": user, "auth": auth, "api_key": api_key, "contract": contract}


@pytest.mark.asyncio
async def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_upload_contract_endpoint(auth_header, client):
    headers = await auth_header

    with patch(
        "app.api.contract.service.ContractService.fetch_from_source"
    ) as mock_fetch:
        # Setup mock return
        mock_response = MagicMock()
        mock_response.model_dump_json.return_value = json.dumps(
            {
                "exists": True,
                "exact_match": True,
                "contract": {"id": "test-id", "address": "0xTEST"},
            }
        )
        mock_fetch.return_value = mock_response

        # Make request
        response = client.post(
            "/contract",
            json={"address": "0xTEST", "network": "ETH"},
            headers=headers,
        )

        assert response.status_code == 202
        assert "contract" in response.json()


@pytest.mark.asyncio
async def test_create_audit_endpoint(auth_header, client):
    headers = await auth_header

    # Create a contract for testing
    contract = await Contract.create(
        address="0xTESTCONTRACT",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        raw_code="contract Test {}",
    )

    with patch("app.api.audit.service.AuditService.process_evaluation") as mock_process:
        # Setup mock return
        mock_response = MagicMock()
        mock_response.model_dump_json.return_value = json.dumps(
            {"id": "test-id", "status": "WAITING"}
        )
        mock_process.return_value = mock_response

        # Make request
        response = client.post(
            "/audit",
            json={
                "contract_id": str(contract.id),
                "audit_type": AuditTypeEnum.SECURITY,
            },
            headers=headers,
        )

        assert response.status_code == 201
        assert "id" in response.json()
        assert "status" in response.json()


@pytest.mark.asyncio
async def test_get_contract_endpoint(auth_header, client):
    headers = await auth_header

    # Create a contract for testing
    contract = await Contract.create(
        address="0xGETCONTRACT",
        network=NetworkEnum.ETH,
        method=ContractMethodEnum.SCAN,
        raw_code="contract Test {}",
    )

    with patch("app.api.contract.service.ContractService.get") as mock_get:
        # Setup mock return
        mock_response = MagicMock()
        mock_response.model_dump_json.return_value = json.dumps(
            {
                "id": str(contract.id),
                "address": "0xGETCONTRACT",
                "code": "contract Test {}",
            }
        )
        mock_get.return_value = mock_response

        # Make request
        response = client.get(
            f"/contract/{contract.id}",
            headers=headers,
        )

        assert response.status_code == 200
        assert "id" in response.json()
        assert "address" in response.json()


@pytest.mark.asyncio
async def test_app_specific_endpoint(app_auth_header, client):
    """Test an endpoint that requires app authentication"""
    headers = await app_auth_header

    with patch("app.api.app.service.AppService.get_info") as mock_get_info:
        # Setup mock return
        mock_response = MagicMock()
        mock_response.model_dump_json.return_value = json.dumps(
            {
                "id": "app-id",
                "name": "Test App",
                "n_users": 10,
                "n_contracts": 5,
                "n_audits": 20,
            }
        )
        mock_get_info.return_value = mock_response

        # Make request
        response = client.get(
            "/app/info",
            headers=headers,
        )

        assert response.status_code == 200
        assert "id" in response.json()
        assert "name" in response.json()


@pytest.mark.asyncio
async def test_first_party_only_endpoint(first_party_auth_header, client):
    """Test an endpoint that requires first party app authentication"""
    headers = await first_party_auth_header

    with patch("app.api.app.service.AppService.get_stats") as mock_get_stats:
        # Setup mock return
        mock_response = MagicMock()
        mock_response.model_dump_json.return_value = json.dumps(
            {"n_apps": 5, "n_users": 100, "n_contracts": 50, "n_audits": 200}
        )
        mock_get_stats.return_value = mock_response

        # Make request
        response = client.get(
            "/app/stats",
            headers=headers,
        )

        assert response.status_code == 200
        assert "n_apps" in response.json()
        assert "n_users" in response.json()
