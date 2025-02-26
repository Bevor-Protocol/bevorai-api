from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "auth" ADD "consumes_credits" BOOL NOT NULL  DEFAULT True;
        COMMENT ON COLUMN "contract"."method" IS 'UPLOAD: upload
SCAN: scan';
        COMMENT ON COLUMN "transaction"."type" IS 'PURCHASE: purchase
SPEND: spend
REFUND: refund';
        ALTER TABLE "user" ALTER COLUMN "used_credits" TYPE DOUBLE PRECISION USING "used_credits"::DOUBLE PRECISION;
        ALTER TABLE "user" ALTER COLUMN "total_credits" TYPE DOUBLE PRECISION USING "total_credits"::DOUBLE PRECISION;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "auth" DROP COLUMN "consumes_credits";
        ALTER TABLE "user" ALTER COLUMN "used_credits" TYPE INT USING "used_credits"::INT;
        ALTER TABLE "user" ALTER COLUMN "total_credits" TYPE INT USING "total_credits"::INT;
        COMMENT ON COLUMN "contract"."method" IS 'UPLOAD: upload
SCAN: scan
CRON: cron';
        COMMENT ON COLUMN "transaction"."type" IS 'PURCHASE: purchase
USE: spend
REFUND: refund';"""
