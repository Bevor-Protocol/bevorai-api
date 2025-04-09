from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "contract" RENAME COLUMN "raw_code" TO "code";
        ALTER TABLE "contract" RENAME COLUMN "hash_code" TO "hashed_code";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "contract" RENAME COLUMN "code" TO "raw_code";
        ALTER TABLE "contract" RENAME COLUMN "hashed_code" TO "hash_code";"""
