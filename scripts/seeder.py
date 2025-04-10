#!/usr/bin/env python3
import asyncio
import os
import sys

# Add the parent directory to Python path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# flake8: noqa: E402
from tortoise import Tortoise

from app.config import TORTOISE_ORM
from app.db.models import App, Auth, Prompt
from app.utils.types.enums import AppTypeEnum, AuditTypeEnum, ClientTypeEnum
from app.utils.backfill.prompts.gas import gas_candidates
from app.utils.backfill.prompts.security import sec_candidates


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
        print("Skipping auth seeder, already exists...")

    prompts = await Prompt.all()

    if await prompts.count() == 0:
        for tag, prompt in sec_candidates.items():
            await Prompt.create(
                audit_type=AuditTypeEnum.SECURITY,
                tag=tag,
                version="0.1",
                content=prompt,
                is_active=True,
            )
        for tag, prompt in gas_candidates.items():
            await Prompt.create(
                audit_type=AuditTypeEnum.GAS,
                tag=tag,
                version="0.1",
                content=prompt,
                is_active=True,
            )
        print("Seeded placeholder prompts")
    else:
        print("Skipping prompt seeder, at least 1 already exists...")

    await Tortoise.close_connections()


def seed_command():
    """Entry point for Poetry script"""
    asyncio.run(seed())
    return 0


if __name__ == "__main__":
    sys.exit(seed_command())
