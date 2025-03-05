from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.dependencies import Authentication, RequireCredits
from app.utils.types.enums import RoleEnum


@pytest.mark.asyncio
async def test_auth_valid_user_token(user_auth, client):
    """Test that a valid user token works for authentication"""
    auth = await user_auth
    response = client.get(
        "/health", headers={"Authorization": f"Bearer {auth['api_key']}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_valid_app_token(app_auth, client):
    """Test that a valid app token works for authentication"""
    auth = await app_auth
    response = client.get(
        "/health", headers={"Authorization": f"Bearer {auth['api_key']}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_invalid_token(client):
    """Test that an invalid token fails authentication"""
    response = client.get(
        "/api/v1/contracts", headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_revoked_token(auth_factory, client):
    """Test that a revoked token fails authentication"""
    revoked_auth = await auth_factory(revoked=True)
    response = client.get(
        "/api/v1/contracts",
        headers={"Authorization": f"Bearer {revoked_auth['api_key']}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_dependency_user_role(mock_auth_state_user):
    """Test Authentication dependency with user role"""
    auth_state = await mock_auth_state_user
    auth = Authentication(required_role=RoleEnum.USER)

    # Mock request with auth state
    class MockRequest:
        def __init__(self):
            self.state = type("obj", (object,), {"auth": auth_state})

    # This should pass without exception
    with patch("app.api.dependencies.Auth.get") as mock_get:
        mock_get.return_value.select_related.return_value = auth_state
        await auth.check_authentication(MockRequest(), "fake_token")


@pytest.mark.asyncio
async def test_auth_dependency_app_role_with_user(mock_auth_state_user):
    """Test Authentication dependency with app role but user token"""
    auth_state = await mock_auth_state_user
    auth = Authentication(required_role=RoleEnum.APP)

    # Mock request with auth state
    class MockRequest:
        def __init__(self):
            self.state = type("obj", (object,), {"auth": auth_state})

    # This should raise an exception
    with pytest.raises(Exception):
        with patch("app.api.dependencies.Auth.get") as mock_get:
            mock_get.return_value.select_related.return_value = auth_state
            await auth.check_authentication(MockRequest(), "fake_token")


@pytest.mark.asyncio
async def test_require_credits_sufficient(mock_auth_state_user, user_auth):
    """Test RequireCredits dependency with sufficient credits"""
    auth_state = await mock_auth_state_user
    auth = await user_auth
    require_credits = RequireCredits()

    # Mock request with auth state
    class MockRequest:
        def __init__(self):
            self.state = type("obj", (object,), {"auth": auth_state})

    # Update user to have sufficient credits
    user = auth["user"]
    user.total_credits = 100
    user.used_credits = 50
    await user.save()

    # This should pass without exception
    await require_credits(MockRequest())


@pytest.mark.asyncio
async def test_require_credits_insufficient(mock_auth_state_user, user_auth):
    """Test RequireCredits dependency with insufficient credits"""
    auth_state = await mock_auth_state_user
    auth = await user_auth
    require_credits = RequireCredits()

    # Mock request with auth state
    class MockRequest:
        def __init__(self):
            self.state = type("obj", (object,), {"auth": auth_state})

    # Update user to have insufficient credits
    user = auth["user"]
    user.total_credits = 100
    user.used_credits = 100
    await user.save()

    # This should raise an exception
    with pytest.raises(HTTPException) as excinfo:
        await require_credits(MockRequest())

    assert excinfo.value.status_code == 402
