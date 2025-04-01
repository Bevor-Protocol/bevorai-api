#!/usr/bin/env python3
import asyncio
import os
import sys

# Add the parent directory to Python path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# flake8: noqa: E402
from tortoise import Tortoise

from app.config import TORTOISE_ORM
from app.db.models import App, Auth
from app.utils.types.enums import AppTypeEnum, ClientTypeEnum


async def init():
    print(TORTOISE_ORM)
    await Tortoise.init(
        config=TORTOISE_ORM,
    )


async def seed():
    await init()

    # Create first party app
    exists = await App.exists(name="certaik", type=AppTypeEnum.FIRST_PARTY)
    if not exists:
        app = await App.create(
            name="certaik",
            type=AppTypeEnum.FIRST_PARTY,
        )
        # Create auth token for app
        api_key, hashed_key = Auth.create_credentials()
        await Auth.create(
            client_type=ClientTypeEnum.APP,
            app=app,
            hashed_key=hashed_key,
        )

        print(f"\nApp created with ID: {app.id}")
        print(f"API Key (unhashed): {api_key}")
    else:
        print("Skipping seeder, already exists...")

    await Tortoise.close_connections()


def seed_command():
    """Entry point for Poetry script"""
    asyncio.run(seed())
    return 0


if __name__ == "__main__":
    sys.exit(seed_command())
