from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "intermediate_response" ADD "processing_time_seconds" INT;
        ALTER TABLE "intermediate_response" ADD "status" VARCHAR(10)   DEFAULT 'waiting';
        ALTER TABLE "intermediate_response" ALTER COLUMN "result" DROP NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "intermediate_response" DROP COLUMN "processing_time_seconds";
        ALTER TABLE "intermediate_response" DROP COLUMN "status";
        ALTER TABLE "intermediate_response" ALTER COLUMN "result" SET NOT NULL;"""
