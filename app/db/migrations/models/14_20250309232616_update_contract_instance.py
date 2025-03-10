from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "contract" ADD "is_parsable" BOOL NOT NULL DEFAULT True;
        ALTER TABLE "contract" ADD "contract_name" TEXT;
        ALTER TABLE "contract" ADD "is_proxy" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "contract" DROP COLUMN "next_attempt_at";
        ALTER TABLE "contract" DROP COLUMN "n_retries";
        COMMENT ON COLUMN "contract"."is_available" IS 'whether source code is available';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "contract" ADD "next_attempt_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "contract" ADD "n_retries" INT NOT NULL DEFAULT 0;
        ALTER TABLE "contract" DROP COLUMN "is_parsable";
        ALTER TABLE "contract" DROP COLUMN "contract_name";
        ALTER TABLE "contract" DROP COLUMN "is_proxy";
        COMMENT ON COLUMN "contract"."is_available" IS 'if via cron, whether source code is available';"""
