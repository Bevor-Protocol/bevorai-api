from tortoise import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from app.utils.types.enums import AuthScopeEnum


async def upgrade(db: BaseDBAsyncClient) -> str:
    async with in_transaction():
        auth_data = await db.execute_query(
            'SELECT id, app_id FROM "auth" ORDER BY created_at LIMIT 1'
        )
        if auth_data[1]:  # Check if any rows were returned
            auth_id = auth_data[1][0][0]  # Get ID from first row
            app_id = auth_data[1][0][1]  # Get app_id from first row

            # Update auth scope using raw SQL
            await db.execute_query(
                'UPDATE "auth" SET scope = $1 WHERE id = $2',
                [AuthScopeEnum.ADMIN.value, auth_id],
            )

            # Update user table
            await db.execute_query('UPDATE "user" SET app_owner_id = $1', [app_id])

    # 🔹 Always return a valid SQL string (using a comment alone does not work)
    return "SELECT * FROM AUTH LIMIT 1;"


async def downgrade(db: BaseDBAsyncClient) -> str:
    return "SELECT * FROM AUTH LIMIT 1;"
