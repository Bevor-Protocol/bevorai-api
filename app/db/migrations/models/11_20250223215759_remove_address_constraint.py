from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
       ALTER TABLE "user" DROP CONSTRAINT user_address_key;
       CREATE INDEX idx_user_address ON "user" (address);
       DROP INDEX IF EXISTS uid_user_address_dcaffb;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS idx_user_address;
        ALTER TABLE "user" ADD CONSTRAINT user_address_key UNIQUE (address);"""
