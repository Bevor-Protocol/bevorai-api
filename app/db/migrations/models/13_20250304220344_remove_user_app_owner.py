from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_user_app_own_c8a42a";
        DROP INDEX IF EXISTS "idx_user_app_own_2e820d";
        ALTER TABLE "user" DROP CONSTRAINT IF EXISTS "fk_user_app_ed6832f0";
        ALTER TABLE "user" DROP COLUMN "app_owner_id";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "app_owner_id" UUID;
        ALTER TABLE "user" ADD CONSTRAINT "fk_user_app_ed6832f0" FOREIGN KEY ("app_owner_id") REFERENCES "app" ("id") ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS "idx_user_app_own_2e820d" ON "user" ("app_owner_id", "address");
        CREATE INDEX IF NOT EXISTS "idx_user_app_own_c8a42a" ON "user" ("app_owner_id");"""
