from tortoise import BaseDBAsyncClient

from app.db.models import App, Permission, User
from app.utils.enums import AppTypeEnum, ClientTypeEnum


async def upgrade(db: BaseDBAsyncClient) -> str:
    apps = await App.all().using_db(db)
    users = await User.all().using_db(db)

    permissions = []
    for app in apps:
        if app != AppTypeEnum.FIRST_PARTY:
            permissions.append(
                Permission(client_type=ClientTypeEnum.APP, app_id=app.id)
            )
    for user in users:
        permissions.append(Permission(client_type=ClientTypeEnum.USER, user_id=user.id))

    await Permission.bulk_create(objects=permissions, using_db=db)

    print(f"backfilled {len(permissions)} permission observations")

    # 🔹 Always return a valid SQL string (using a comment alone does not work)
    return "SELECT * FROM PERMISSION LIMIT 1;"


async def downgrade(db: BaseDBAsyncClient) -> str:
    return "SELECT * FROM PERMISSION LIMIT 1;"
