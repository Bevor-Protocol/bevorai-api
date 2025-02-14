from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "auth" DROP CONSTRAINT IF EXISTS "fk_auth_app_1acfffa3";
        ALTER TABLE "auth" DROP CONSTRAINT IF EXISTS "fk_auth_user_37975f77";
        ALTER TABLE "auth" ADD CONSTRAINT "fk_auth_user_37975f77" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE;
        ALTER TABLE "auth" ADD CONSTRAINT "fk_auth_app_1acfffa3" FOREIGN KEY ("app_id") REFERENCES "app" ("id") ON DELETE CASCADE;
        CREATE UNIQUE INDEX "uid_auth_user_id_cbe8d3" ON "auth" ("user_id");
        CREATE UNIQUE INDEX "uid_auth_app_id_0a01c8" ON "auth" ("app_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_auth_app_id_0a01c8";
        DROP INDEX IF EXISTS "uid_auth_user_id_cbe8d3";
        ALTER TABLE "auth" DROP CONSTRAINT IF EXISTS "fk_auth_app_1acfffa3";
        ALTER TABLE "auth" DROP CONSTRAINT IF EXISTS "fk_auth_user_37975f77";
        ALTER TABLE "auth" ADD CONSTRAINT "fk_auth_user_37975f77" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE SET NULL;
        ALTER TABLE "auth" ADD CONSTRAINT "fk_auth_app_1acfffa3" FOREIGN KEY ("app_id") REFERENCES "app" ("id") ON DELETE SET NULL;"""
