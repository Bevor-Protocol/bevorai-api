from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "auth" ADD "scope" VARCHAR(5) NOT NULL  DEFAULT 'write';
        ALTER TABLE "auth" ADD "revoked_at" TIMESTAMPTZ;
        ALTER TABLE "auth" DROP COLUMN "is_revoked";
        ALTER TABLE "user" ADD "app_owner_id" UUID;
        ALTER TABLE "user" ADD CONSTRAINT "fk_user_app_ed6832f0" FOREIGN KEY ("app_owner_id") REFERENCES "app" ("id") ON DELETE CASCADE;
        CREATE INDEX "idx_user_app_own_c8a42a" ON "user" ("app_owner_id");
        CREATE INDEX "idx_user_app_own_2e820d" ON "user" ("app_owner_id", "address");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_user_app_own_2e820d";
        DROP INDEX IF EXISTS "idx_user_app_own_c8a42a";
        ALTER TABLE "user" DROP CONSTRAINT IF EXISTS "fk_user_app_ed6832f0";
        ALTER TABLE "auth" ADD "is_revoked" BOOL NOT NULL  DEFAULT False;
        ALTER TABLE "auth" DROP COLUMN "scope";
        ALTER TABLE "auth" DROP COLUMN "revoked_at";
        ALTER TABLE "user" DROP COLUMN "app_owner_id";"""
