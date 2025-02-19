from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "permission" RENAME COLUMN "permission_type" TO "client_type";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "permission" RENAME COLUMN "client_type" TO "permission_type";"""
