from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "audit" ADD "version" VARCHAR(20)   DEFAULT 'v1';
        ALTER TABLE "audit" DROP COLUMN "model";
        ALTER TABLE "intermediate_response" ALTER COLUMN "step" TYPE VARCHAR(30) USING "step"::VARCHAR(30);
        COMMENT ON COLUMN "intermediate_response"."step" IS NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "audit" ADD "model" VARCHAR(255);
        ALTER TABLE "audit" DROP COLUMN "version";
        ALTER TABLE "intermediate_response" ALTER COLUMN "step" TYPE VARCHAR(9) USING "step"::VARCHAR(9);
        COMMENT ON COLUMN "intermediate_response"."step" IS 'CANDIDATE: candidate
REVIEWER: reviewer
REPORTER: reporter';"""
