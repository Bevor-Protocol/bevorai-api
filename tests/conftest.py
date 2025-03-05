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


@pytest_asyncio.fixture(scope="session")
async def user_factory():
    """Factory to create users with different attributes"""

    async def _create_user(address: str, total_credits: float = 100.0) -> User:

        user = await User.create(
            address=address, total_credits=total_credits, used_credits=0.0
        )
        return user

    return _create_user


@pytest_asyncio.fixture(scope="session")
async def app_factory():
    """Factory to create apps with different attributes"""

    async def _create_app(
        name: str = "Test App",
        app_type: AppTypeEnum = AppTypeEnum.THIRD_PARTY,
        owner: User | None = None,
    ) -> App:
        if app_type == AppTypeEnum.THIRD_PARTY:
            if not owner:
                raise Exception("owner_address is required")

        app = await App.create(name=name, type=app_type, owner=owner)
        return app

    return _create_app


@pytest_asyncio.fixture(scope="session")
async def first_party_app():
    return await App.create(type=AppTypeEnum.FIRST_PARTY, name="test")


@pytest_asyncio.fixture(scope="session")
async def standard_user(user_factory):
    """Create a standard user"""
    return await user_factory(address="0xuser")


@pytest_asyncio.fixture(scope="session")
async def third_party_app(app_factory, standard_user):
    """Create a third-party app with a user owner"""
    return await app_factory(
        name="Third Party Test App",
        app_type=AppTypeEnum.THIRD_PARTY,
        owner=standard_user,
    )
