import logging

import pytest
from tortoise import Tortoise

from app.db.models import App, Auth
from app.utils.types.enums import AppTypeEnum

# @pytest.mark.asyncio
# async def test_database_initialization():
#     """Test that the database is properly initialized"""

#     auth = await App.filter(type=AppTypeEnum.FIRST_PARTY).first()

#     assert auth
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_example(first_party_app):
    logger.info("OK")
    logger.info(first_party_app)
    assert True


def test_example2():
    logger.info("HERE")
    assert True


# async def test_user_factory(user_factory, test_db):
#     """Test that the user factory creates users correctly"""
#     user = await user_factory(address="0xtest", total_credits=50.0)
#     assert user.address == "0xtest"
#     assert user.total_credits == 50.0
#     assert user.used_credits == 0.0


# async def test_app_factory(app_factory, user_factory, test_db):
#     """Test that the app factory creates apps correctly"""
#     owner = await user_factory()
#     app = await app_factory(
#         name="Test Factory App", app_type=AppTypeEnum.THIRD_PARTY, owner=owner
#     )
#     assert app.name == "Test Factory App"
#     assert app.type == AppTypeEnum.THIRD_PARTY
#     assert app.owner.id == owner.id


# async def test_auth_factory(auth_factory, test_db):
#     """Test that the auth factory creates auth tokens correctly"""
#     # Test user auth
#     user_auth_data = await auth_factory(client_type=ClientTypeEnum.USER)
#     assert user_auth_data["auth"] is not None
#     assert user_auth_data["api_key"] is not None
#     assert user_auth_data["user"] is not None
#     assert user_auth_data["app"] is None

#     # Test app auth
#     app_auth_data = await auth_factory(client_type=ClientTypeEnum.APP)
#     assert app_auth_data["auth"] is not None
#     assert app_auth_data["api_key"] is not None
#     assert app_auth_data["user"] is not None
#     assert app_auth_data["app"] is not None


# async def test_auth_headers(auth_header, app_auth_header, first_party_auth_header):
#     """Test that auth headers are created correctly"""
#     assert "Authorization" in auth_header
#     assert auth_header["Authorization"].startswith("Bearer ")

#     assert "Authorization" in app_auth_header
#     assert app_auth_header["Authorization"].startswith("Bearer ")

#     assert "Authorization" in first_party_auth_header
#     assert first_party_auth_header["Authorization"].startswith("Bearer ")


# async def test_auth_states(
#     mock_auth_state_user, mock_auth_state_app, mock_auth_state_first_party
# ):
#     """Test that auth states are created correctly"""
#     # User auth state
#     assert mock_auth_state_user.role == RoleEnum.USER
#     assert mock_auth_state_user.user_id is not None
#     assert mock_auth_state_user.app_id is None
#     assert mock_auth_state_user.consumes_credits is True

#     # App auth state
#     assert mock_auth_state_app.role == RoleEnum.APP
#     assert mock_auth_state_app.user_id is not None
#     assert mock_auth_state_app.app_id is not None
#     assert mock_auth_state_app.consumes_credits is True

#     # First party app auth state
#     assert mock_auth_state_first_party.role == RoleEnum.APP_FIRST_PARTY
#     assert mock_auth_state_first_party.user_id is None
#     assert mock_auth_state_first_party.app_id is not None
#     assert mock_auth_state_first_party.consumes_credits is False
