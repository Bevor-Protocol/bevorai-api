from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_audit_job_id_1dd2f4";
        ALTER TABLE "audit" DROP COLUMN "job_id";
        ALTER TABLE "audit" ALTER COLUMN "model" DROP NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "audit" ADD "job_id" VARCHAR(255) NOT NULL UNIQUE;
        ALTER TABLE "audit" ALTER COLUMN "model" SET NOT NULL;
        CREATE UNIQUE INDEX "uid_audit_job_id_1dd2f4" ON "audit" ("job_id");"""
