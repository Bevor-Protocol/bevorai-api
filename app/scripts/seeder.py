import asyncio

from tortoise import Tortoise

from app.config import TORTOISE_ORM
from app.db.models import App, Auth
from app.utils.enums import AppTypeEnum, ClientTypeEnum


async def init():
    print(TORTOISE_ORM)
    await Tortoise.init(
        config=TORTOISE_ORM,
    )
    await Tortoise.generate_schemas()


async def seed():
    await init()
    # Create first party app
    app = await App.create(
        name="certaik local",
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

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed())
