from tortoise import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from app.db.models import Auth, User
from app.utils.enums import AuthScopeEnum


async def upgrade(db: BaseDBAsyncClient) -> str:
    async with in_transaction():
        auth = await Auth.first(using_db=db).select_related("app")
        app_id = auth.app.id
        auth.scope = AuthScopeEnum.ADMIN
        await auth.save()

        try:
            users = await User.all().using_db(db)
            for user in users:
                user.app_owner_id = app_id

            await User.bulk_update(users, fields=["app_owner_id"], using_db=db)

            print(f"backfilled {len(users)} app_owner_id")
        except Exception as err:
            # tmp differential between tortoise +
            print(f"Error: {err}")

    # 🔹 Always return a valid SQL string (using a comment alone does not work)
    return "SELECT * FROM AUTH LIMIT 1;"


async def downgrade(db: BaseDBAsyncClient) -> str:
    return "SELECT * FROM AUTH LIMIT 1;"
