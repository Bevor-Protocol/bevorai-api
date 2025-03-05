import asyncio
import logging
import os
import sys
import uuid
from typing import Dict, Optional

import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# flake8: noqa E402

# tests/conftest.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tortoise import Tortoise
from tortoise.contrib.test import _init_db, finalizer, getDBConfig, initializer

from app.db.models import User  # Replace with your actual model
from app.db.models import App, Auth
from app.main import app as main_app
from app.utils.schema.dependencies import AuthState
from app.utils.types.enums import AppTypeEnum, ClientTypeEnum, RoleEnum

logger = logging.getLogger(__name__)

TEST_DB_URL = "sqlite://:memory:"

TEST_TORTOISE_ORM = {
    "connections": {"default": TEST_DB_URL},
    "apps": {
        "models": {
            "models": ["app.db.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}


# @pytest.fixture(scope="session", autouse=True)
# async def initialize_test_db():
#     await Tortoise.init(config=TEST_TORTOISE_ORM)
#     await Tortoise.generate_schemas()
#     logger.info("INITIALIZED")
#     yield
#     await Tortoise.close_connections()


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def in_memory_db(request, event_loop):
    # Initialize the in-memory database
    event_loop.run_until_complete(Tortoise.init(config=TEST_TORTOISE_ORM))
    # Generate schemas with safe=True to handle cyclic dependencies
    event_loop.run_until_complete(Tortoise.generate_schemas(safe=True))

    def finalizer():
        event_loop.run_until_complete(Tortoise._drop_databases())
        event_loop.run_until_complete(Tortoise.close_connections())

    request.addfinalizer(finalizer)


@pytest.fixture(scope="session")
def test_me():
    return "test"


@pytest_asyncio.fixture(scope="session")
async def first_party_app():
    return await App.create(type=AppTypeEnum.FIRST_PARTY, name="test")


# @pytest.fixture
# async def admin_user():
#     return await User.create(username="admin", is_admin=True)


# @pytest.fixture
# async def regular_user():
#     return await User.create(username="regular", is_admin=False)


# tests/test_api.py
# import pytest
# from httpx import AsyncClient

# from app.main import app


# @pytest.mark.asyncio
# async def test_create_item():
#     async with AsyncClient(app=app, base_url="http://test") as client:
#         response = await client.post("/items/", json={"name": "Test Item"})
#         assert response.status_code == 201
#         data = response.json()
#         assert data["name"] == "Test Item"


# @pytest.fixture
# async def user_factory():
#     """Factory to create users with different attributes"""

#     async def _create_user(address: Optional[str] = None, total_credits: float = 100.0):
#         if not address:
#             address = f"0x{uuid.uuid4().hex[:40]}"

#         user = await User.create(
#             address=address, total_credits=total_credits, used_credits=0.0
#         )
#         return user

#     return _create_user


# @pytest.fixture
# async def app_factory(user_factory):
#     """Factory to create apps with different attributes"""

#     async def _create_app(
#         name: str = "Test App",
#         app_type: AppTypeEnum = AppTypeEnum.THIRD_PARTY,
#         owner=None,
#     ):
#         if not owner:
#             owner = await user_factory()

#         app = await App.create(owner=owner, name=name, type=app_type)
#         return app

#     return _create_app


# @pytest.fixture
# async def auth_factory(user_factory, app_factory):
#     """Factory to create auth tokens for users or apps"""

#     async def _create_auth(
#         client_type: ClientTypeEnum = ClientTypeEnum.USER,
#         user=None,
#         app=None,
#         revoked: bool = False,
#     ):
#         if client_type == ClientTypeEnum.USER and not user:
#             user = await user_factory()

#         if client_type == ClientTypeEnum.APP and not app:
#             app = await app_factory()

#         api_key, hashed_key = Auth.create_credentials()

#         auth_data = {
#             "client_type": client_type,
#             "hashed_key": hashed_key,
#         }

#         if client_type == ClientTypeEnum.USER:
#             auth_data["user"] = user
#         else:
#             auth_data["app"] = app

#         if revoked:
#             from datetime import datetime

#             auth_data["revoked_at"] = datetime.now()

#         auth = await Auth.create(**auth_data)

#         return {
#             "auth": auth,
#             "api_key": api_key,
#             "user": (
#                 user
#                 if client_type == ClientTypeEnum.USER
#                 else app.owner if app else None
#             ),
#             "app": app if client_type == ClientTypeEnum.APP else None,
#         }

#     return _create_auth


# @pytest.fixture
# async def user_auth(auth_factory) -> Dict:
#     """Create a standard user auth token"""
#     return await auth_factory(client_type=ClientTypeEnum.USER)


# @pytest.fixture
# async def app_auth(auth_factory) -> Dict:
#     """Create a standard app auth token"""
#     return await auth_factory(client_type=ClientTypeEnum.APP)


# @pytest.fixture
# async def first_party_app_auth(user_factory, auth_factory) -> Dict:
#     """Create a first party app auth token"""
#     owner = await user_factory()
#     app = await App.create(
#         owner=owner, name="First Party App", type=AppTypeEnum.FIRST_PARTY
#     )
#     return await auth_factory(client_type=ClientTypeEnum.APP, app=app)


# @pytest.fixture
# async def auth_header(user_auth) -> Dict[str, str]:
#     """Return authorization header with user token"""
#     auth = await user_auth
#     return {"Authorization": f"Bearer {auth['api_key']}"}


# @pytest.fixture
# async def app_auth_header(app_auth) -> Dict[str, str]:
#     """Return authorization header with app token"""
#     auth = await app_auth
#     return {"Authorization": f"Bearer {auth['api_key']}"}


# @pytest.fixture
# async def first_party_auth_header(first_party_app_auth) -> Dict[str, str]:
#     """Return authorization header with first party app token"""
#     auth = await first_party_app_auth
#     return {"Authorization": f"Bearer {auth['api_key']}"}


# @pytest.fixture
# async def mock_auth_state_user(user_auth) -> AuthState:
#     """Create a mock AuthState for a user"""
#     auth = await user_auth
#     return AuthState(
#         role=RoleEnum.USER,
#         user_id=str(auth["user"].id),
#         app_id=None,
#         is_delegated=False,
#         consumes_credits=True,
#         credit_consumer_user_id=str(auth["user"].id),
#     )


# @pytest.fixture
# async def mock_auth_state_app(app_auth) -> AuthState:
#     """Create a mock AuthState for an app"""
#     auth = await app_auth
#     return AuthState(
#         role=RoleEnum.APP,
#         user_id=str(auth["app"].owner.id),
#         app_id=str(auth["app"].id),
#         is_delegated=False,
#         consumes_credits=True,
#         credit_consumer_user_id=str(auth["app"].owner.id),
#     )


# @pytest.fixture
# async def mock_auth_state_first_party(first_party_app_auth) -> AuthState:
#     """Create a mock AuthState for a first party app"""
#     auth = await first_party_app_auth
#     return AuthState(
#         role=RoleEnum.APP_FIRST_PARTY,
#         user_id=None,
#         app_id=str(auth["app"].id),
#         is_delegated=False,
#         consumes_credits=False,
#         credit_consumer_user_id=None,
#     )
