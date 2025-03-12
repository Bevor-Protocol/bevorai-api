import pytest
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.blockchain.service import BlockchainService
from app.api.dependencies import Authentication
from app.db.models import Auth, Transaction, User
from app.utils.types.enums import ClientTypeEnum, RoleEnum, TransactionTypeEnum
from tests.constants import (
    FIRST_PARTY_APP_API_KEY,
    THIRD_PARTY_APP_API_KEY,
    USER_API_KEY,
)


@pytest.mark.anyio
async def test_auth_dependency_first_party(first_party_app):
    """
    Test that the Authentication dependency correctly processes headers
    and sets the auth state on the request object
    """
    # Create a mock request
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    # Create an Authentication instance with required role
    auth_dependency = Authentication(required_role=RoleEnum.APP_FIRST_PARTY)

    # Test with first party app credentials
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=FIRST_PARTY_APP_API_KEY
    )

    # Call the dependency directly
    await auth_dependency(
        request=mock_request, authorization=credentials, bevor_user_identifier=None
    )

    # Verify the auth state was set correctly
    assert hasattr(mock_request.state, "auth")
    assert mock_request.state.auth.role == RoleEnum.APP_FIRST_PARTY
    assert mock_request.state.auth.consumes_credits is False
    assert mock_request.state.auth.is_delegated is False

    """confirm it can still call APP scope"""
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    auth_dependency = Authentication(required_role=RoleEnum.APP)

    await auth_dependency(
        request=mock_request, authorization=credentials, bevor_user_identifier=None
    )

    # Verify the auth state was set correctly
    assert hasattr(mock_request.state, "auth")
    assert mock_request.state.auth.role == RoleEnum.APP_FIRST_PARTY
    assert mock_request.state.auth.consumes_credits is False
    assert mock_request.state.auth.is_delegated is False

    """confirm it can still call USER scope"""
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    auth_dependency = Authentication(required_role=RoleEnum.USER)

    await auth_dependency(
        request=mock_request, authorization=credentials, bevor_user_identifier=None
    )

    # Verify the auth state was set correctly
    assert hasattr(mock_request.state, "auth")
    assert mock_request.state.auth.role == RoleEnum.APP_FIRST_PARTY
    assert mock_request.state.auth.consumes_credits is False
    assert mock_request.state.auth.is_delegated is False


@pytest.mark.anyio
async def test_auth_dependency_third_party(third_party_app):
    """
    Test that the Authentication dependency correctly processes headers
    and sets the auth state on the request object
    """
    # Create a mock request
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    # Create an Authentication instance with required role
    auth_dependency = Authentication(required_role=RoleEnum.APP_FIRST_PARTY)

    # Test with first party app credentials
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=THIRD_PARTY_APP_API_KEY
    )

    # Call the dependency directly
    # This should fail with a 401 since third_party_app can't use APP_FIRST_PARTY role
    with pytest.raises(HTTPException) as excinfo:
        await auth_dependency(
            request=mock_request, authorization=credentials, bevor_user_identifier=None
        )
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED

    """confirm it can call APP scope"""
    auth_dependency = Authentication(required_role=RoleEnum.APP)
    await auth_dependency(
        request=mock_request, authorization=credentials, bevor_user_identifier=None
    )

    # Verify the auth state was set correctly
    assert hasattr(mock_request.state, "auth")
    assert mock_request.state.auth.role == RoleEnum.APP
    assert mock_request.state.auth.consumes_credits is True
    assert mock_request.state.auth.is_delegated is False

    """confirm it can still call USER scope"""
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    auth_dependency = Authentication(required_role=RoleEnum.USER)

    await auth_dependency(
        request=mock_request, authorization=credentials, bevor_user_identifier=None
    )

    # Verify the auth state was set correctly
    assert hasattr(mock_request.state, "auth")
    assert mock_request.state.auth.role == RoleEnum.APP
    assert mock_request.state.auth.consumes_credits is True
    assert mock_request.state.auth.is_delegated is False


@pytest.mark.anyio
async def test_auth_dependency_user(user_with_auth):
    """
    Test that the Authentication dependency correctly processes headers
    and sets the auth state on the request object
    """
    # Create a mock request
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    # Create an Authentication instance with required role
    auth_dependency = Authentication(required_role=RoleEnum.APP_FIRST_PARTY)

    # Test with first party app credentials
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=USER_API_KEY
    )
    with pytest.raises(HTTPException) as excinfo:
        await auth_dependency(
            request=mock_request, authorization=credentials, bevor_user_identifier=None
        )
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED

    auth_dependency = Authentication(required_role=RoleEnum.APP)
    with pytest.raises(HTTPException) as excinfo:
        await auth_dependency(
            request=mock_request, authorization=credentials, bevor_user_identifier=None
        )
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED

    """confirm it can still call USER scope"""
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    auth_dependency = Authentication(required_role=RoleEnum.USER)

    await auth_dependency(
        request=mock_request, authorization=credentials, bevor_user_identifier=None
    )

    # Verify the auth state was set correctly
    assert hasattr(mock_request.state, "auth")
    assert mock_request.state.auth.role == RoleEnum.USER
    assert mock_request.state.auth.consumes_credits is True
    assert mock_request.state.auth.is_delegated is False


@pytest.mark.anyio
async def test_auth_with_delegation(
    first_party_app, third_party_app, user_with_auth, standard_user
):
    """Confirm first party can delegate to user"""
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    auth_dependency = Authentication(required_role=RoleEnum.USER)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=FIRST_PARTY_APP_API_KEY
    )

    await auth_dependency(
        request=mock_request,
        authorization=credentials,
        bevor_user_identifier=str(user_with_auth.id),
    )

    # Verify the auth state was set correctly
    assert hasattr(mock_request.state, "auth")
    assert mock_request.state.auth.role == RoleEnum.APP_FIRST_PARTY
    assert mock_request.state.auth.consumes_credits is False
    assert mock_request.state.auth.is_delegated is True
    assert str(mock_request.state.auth.user_id) == str(user_with_auth.id)
    assert str(mock_request.state.auth.app_id) == str(first_party_app.id)

    """Confirm third party can delegate to user"""
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    auth_dependency = Authentication(required_role=RoleEnum.USER)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=THIRD_PARTY_APP_API_KEY
    )

    await auth_dependency(
        request=mock_request,
        authorization=credentials,
        bevor_user_identifier=str(user_with_auth.id),
    )

    # Verify the auth state was set correctly
    assert hasattr(mock_request.state, "auth")
    assert mock_request.state.auth.role == RoleEnum.APP
    assert mock_request.state.auth.consumes_credits is True
    assert mock_request.state.auth.is_delegated is True
    assert str(mock_request.state.auth.user_id) == str(user_with_auth.id)
    assert str(mock_request.state.auth.app_id) == str(third_party_app.id)

    """Confirm user cannot delegate, even if it tries"""
    mock_request = Request(
        scope={
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/test",
        }
    )

    auth_dependency = Authentication(required_role=RoleEnum.USER)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=USER_API_KEY
    )

    await auth_dependency(
        request=mock_request,
        authorization=credentials,
        bevor_user_identifier=str(standard_user.id),
    )

    # Verify the auth state was set correctly
    assert hasattr(mock_request.state, "auth")
    assert mock_request.state.auth.role == RoleEnum.USER
    assert mock_request.state.auth.consumes_credits is True
    assert mock_request.state.auth.is_delegated is False
    assert str(mock_request.state.auth.user_id) == str(user_with_auth.id)
    assert mock_request.state.auth.app_id is None


@pytest.mark.anyio
async def test_auth_generate_api_key(
    first_party_app, user_with_permission, async_client
):
    """
    Test that the generate_api_key endpoint works with first party app authentication
    """
    # Make a request to generate an API key for a user
    response = await async_client.post(
        f"/auth/{ClientTypeEnum.USER.value}",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(user_with_permission.id),
        },
    )

    # Check that the request was successful
    assert response.status_code == 202
    # Check that the response contains an API key
    assert "api_key" in response.json()

    # The API key should be a non-empty string
    api_key = response.json()["api_key"]  # type: ignore
    assert isinstance(api_key, str)
    assert len(api_key) > 0

    auth = await Auth.get(user_id=user_with_permission.id)
    assert auth.hashed_key == Auth.hash_key(api_key)
    await auth.delete()


@pytest.mark.anyio
async def test_auth_generate_api_key_unauthorized(
    user_with_auth, user_with_permission, async_client
):
    """
    Test that the generate_api_key endpoint can't be called from user auth.
    """
    # Make a request to generate an API key for a user
    response = await async_client.post(
        f"/auth/{ClientTypeEnum.USER.value}",
        headers={
            "Authorization": f"Bearer {USER_API_KEY}",
            "Bevor-User-Identifier": str(user_with_permission.id),
        },
    )

    # Check that the request was successful
    assert response.status_code == 401


@pytest.mark.anyio
async def test_auth_generate_api_key_wrong_permissions(
    first_party_app, standard_user, async_client
):
    """
    Test that auth can't be generated if user doesn't have permissions.
    """
    # Make a request to generate an API key for a user
    response = await async_client.post(
        f"/auth/{ClientTypeEnum.USER.value}",
        headers={
            "Authorization": f"Bearer {FIRST_PARTY_APP_API_KEY}",
            "Bevor-User-Identifier": str(standard_user.id),
        },
    )

    # Check that the request was successful
    assert response.status_code == 401


@pytest.mark.anyio
async def test_credit_sync_mocked(async_client, monkeypatch):
    """
    Test that the authentication dependency check works correctly for the
    sync_credits endpoint without executing the endpoint logic
    """
    ADDRESS = "0xtest"
    user = await User.create(address=ADDRESS, total_credits=100)
    api_key, hashed_key = Auth.create_credentials()
    await Auth.create(user=user, client_type=ClientTypeEnum.USER, hashed_key=hashed_key)

    # Mock the sync_credits method that will be called after dependency check
    original_get_credits = BlockchainService.get_credits

    # Track if the method was called
    method_called = False

    async def mock_get_credits_inc(self, address):
        nonlocal method_called
        method_called = True
        # Return a simple credit value
        return 150.0

    async def mock_get_credits_dec(self, address):
        nonlocal method_called
        method_called = True
        # Return a simple credit value
        return 100.0

    # Apply the mock to the blockchain service's get_credits method
    monkeypatch.setattr(BlockchainService, "get_credits", mock_get_credits_inc)

    # Should INCREMENT credits by 50
    response = await async_client.post(
        "/auth/sync/credits",
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 200
    assert method_called
    data = response.json()
    assert data["total_credits"] == 150  # type: ignore
    assert data["credits_added"] == 150 - 100  # type: ignore
    assert data["credits_removed"] == 0  # type: ignore

    transactions = await Transaction.filter(user_id=user.id)
    assert len(transactions) == 1
    assert transactions[0].type == TransactionTypeEnum.PURCHASE
    assert transactions[0].amount == 150 - 100

    await Transaction.filter(user_id=user.id).delete()

    # refetch user, which was updated in api call
    user = await User.get(id=user.id)
    assert user.total_credits == 150
    method_called = False

    monkeypatch.setattr(BlockchainService, "get_credits", mock_get_credits_dec)

    # Should DECREMENT credits by 50
    response = await async_client.post(
        "/auth/sync/credits",
        headers={"Authorization": f"Bearer {api_key}"},
    )

    assert response.status_code == 200
    assert method_called
    data = response.json()
    assert data["total_credits"] == 100  # type: ignore
    assert data["credits_added"] == 0  # type: ignore
    assert data["credits_removed"] == 50  # type: ignore

    transactions = await Transaction.filter(user_id=user.id)
    assert len(transactions) == 1
    assert transactions[0].type == TransactionTypeEnum.REFUND
    assert transactions[0].amount == 50

    await Transaction.filter(user_id=user.id).delete()

    # refetch user, which was updated in api call
    user = await User.get(id=user.id)
    user_id = user.id
    assert user.total_credits == 100

    method_called = False

    # Restore the original method
    monkeypatch.setattr(BlockchainService, "get_credits", original_get_credits)

    assert await Auth.exists(user_id=user_id)
    await user.delete()
    # confirm cascading
    assert not await Auth.exists(user_id=user_id)
