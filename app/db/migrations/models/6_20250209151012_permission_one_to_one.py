from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "permission" DROP CONSTRAINT IF EXISTS "fk_permissi_user_1d9d6834";
        ALTER TABLE "permission" DROP CONSTRAINT IF EXISTS "fk_permissi_app_0b76b9fc";
        ALTER TABLE "permission" ADD CONSTRAINT "fk_permissi_app_0b76b9fc" FOREIGN KEY ("app_id") REFERENCES "app" ("id") ON DELETE CASCADE;
        ALTER TABLE "permission" ADD CONSTRAINT "fk_permissi_user_1d9d6834" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE;
        CREATE UNIQUE INDEX "uid_permission_app_id_6bf73e" ON "permission" ("app_id");
        CREATE UNIQUE INDEX "uid_permission_user_id_097924" ON "permission" ("user_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_permission_user_id_097924";
        DROP INDEX IF EXISTS "uid_permission_app_id_6bf73e";
        ALTER TABLE "permission" DROP CONSTRAINT IF EXISTS "fk_permissi_user_1d9d6834";
        ALTER TABLE "permission" DROP CONSTRAINT IF EXISTS "fk_permissi_app_0b76b9fc";
        ALTER TABLE "permission" ADD CONSTRAINT "fk_permissi_app_0b76b9fc" FOREIGN KEY ("app_id") REFERENCES "app" ("id") ON DELETE CASCADE;
        ALTER TABLE "permission" ADD CONSTRAINT "fk_permissi_user_1d9d6834" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE;"""
