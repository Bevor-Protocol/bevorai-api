from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "webhook" DROP CONSTRAINT IF EXISTS "fk_webhook_app_id_app_id";
        ALTER TABLE "webhook" DROP CONSTRAINT IF EXISTS "fk_webhook_user_id_user_id";
        ALTER TABLE "webhook" ADD CONSTRAINT "fk_webhook_app_id_app_id" FOREIGN KEY ("app_id") REFERENCES "app" ("id") ON DELETE CASCADE;
        ALTER TABLE "webhook" ADD CONSTRAINT "fk_webhook_user_id_user_id" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE CASCADE;

        COMMENT ON COLUMN "contract"."network" IS 'ETH: eth
BSC: bsc
POLYGON: polygon
BASE: base
AVAX: avax
MODE: mode
ARB: arb
ETH_SEPOLIA: eth_sepolia
BSC_TEST: bsc_test
POLYGON_AMOY: polygon_amoy
BASE_SEPOLIA: base_sepolia
AVAX_FUJI: avax_fuji
MODE_TESTNET: mode_testnet
ARB_SEPOLIA: arb_sepolia';
        CREATE TABLE IF NOT EXISTS "permission" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "permission_type" VARCHAR(4) NOT NULL,
    "can_create_app" BOOL NOT NULL  DEFAULT False,
    "can_create_api_key" BOOL NOT NULL  DEFAULT False,
    "app_id" UUID REFERENCES "app" ("id") ON DELETE CASCADE,
    "user_id" UUID REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_permission_user_id_097924" ON "permission" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_permission_app_id_6bf73e" ON "permission" ("app_id");
COMMENT ON COLUMN "permission"."permission_type" IS 'USER: user\nAPP: app';
        CREATE INDEX "idx_finding_audit_i_d5a365" ON "finding" ("audit_id", "level");
        CREATE INDEX "idx_finding_audit_i_033cad" ON "finding" ("audit_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "webhook" DROP CONSTRAINT IF EXISTS "fk_webhook_app_id_app_id";
        ALTER TABLE "webhook" DROP CONSTRAINT IF EXISTS "fk_webhook_user_id_user_id";
        ALTER TABLE "webhook" ADD CONSTRAINT "fk_webhook_app_id_app_id" FOREIGN KEY ("app_id") REFERENCES "app" ("id") ON DELETE SET NULL;
        ALTER TABLE "webhook" ADD CONSTRAINT "fk_webhook_user_id_user_id" FOREIGN KEY ("user_id") REFERENCES "user" ("id") ON DELETE SET NULL;

        DROP INDEX IF EXISTS "idx_finding_audit_i_033cad";
        DROP INDEX IF EXISTS "idx_finding_audit_i_d5a365";
        COMMENT ON COLUMN "contract"."network" IS 'ETH: eth
BSC: bsc
POLYGON: polygon
BASE: base
ETH_SEPOLIA: eth_sepolia
BSC_TEST: bsc_test
POLYGON_AMOY: polygon_amoy
BASE_SEPOLIA: base_sepolia';
        DROP TABLE IF EXISTS "permission";"""
