from tortoise import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from app.db.models import Auth
from app.utils.enums import AuthScopeEnum


async def upgrade(db: BaseDBAsyncClient) -> str:
    async with in_transaction():
        auth = await Auth.first(using_db=db).select_related("app")
        app_id = auth.app.id
        auth.scope = AuthScopeEnum.ADMIN
        await auth.save()

    return f"""
    UPDATE "user" SET app_owner_id = {app_id};
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return "SELECT * FROM AUTH LIMIT 1;"
