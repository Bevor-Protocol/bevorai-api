from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "chat" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "is_visible" BOOL NOT NULL DEFAULT True,
    "total_messages" INT NOT NULL DEFAULT 0,
    "audit_id" UUID NOT NULL REFERENCES "audit" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_chat_user_id_587b99" ON "chat" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_chat_audit_i_754664" ON "chat" ("audit_id");
CREATE INDEX IF NOT EXISTS "idx_chat_is_visi_efd46d" ON "chat" ("is_visible", "user_id");
        CREATE TABLE IF NOT EXISTS "chat_message" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "chat_role" VARCHAR(6) NOT NULL,
    "message" TEXT NOT NULL,
    "n_tokens" INT NOT NULL,
    "model_name" TEXT NOT NULL,
    "embedding" JSONB,
    "chat_id" UUID NOT NULL REFERENCES "chat" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_chat_messag_chat_id_e94634" ON "chat_message" ("chat_id");
COMMENT ON COLUMN "chat_message"."chat_role" IS 'USER: user\nSYSTEM: system';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "chat_message";
        DROP TABLE IF EXISTS "chat";"""
