from tortoise import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from app.db.models import Auth
from app.utils.types.enums import AuthScopeEnum


async def upgrade(db: BaseDBAsyncClient) -> str:
    async with in_transaction():
        auth = await Auth.first(using_db=db).select_related("app")
        app_id = auth.app.id
        auth.scope = AuthScopeEnum.ADMIN
        await auth.save()

        await db.execute_query('UPDATE "user" SET app_owner_id = $1', [app_id])

    # 🔹 Always return a valid SQL string (using a comment alone does not work)
    return "SELECT * FROM AUTH LIMIT 1;"


async def downgrade(db: BaseDBAsyncClient) -> str:
    return "SELECT * FROM AUTH LIMIT 1;"
