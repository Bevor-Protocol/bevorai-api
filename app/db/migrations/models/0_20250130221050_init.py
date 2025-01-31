from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "contract" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "method" VARCHAR(6) NOT NULL,
    "is_available" BOOL NOT NULL  DEFAULT True,
    "n_retries" INT NOT NULL  DEFAULT 0,
    "next_attempt_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "address" VARCHAR(255),
    "network" VARCHAR(12),
    "raw_code" TEXT,
    "hash_code" VARCHAR(255)
);
COMMENT ON COLUMN "contract"."method" IS 'UPLOAD: upload\nSCAN: scan\nCRON: cron';
COMMENT ON COLUMN "contract"."is_available" IS 'if via cron, whether source code is available';
COMMENT ON COLUMN "contract"."n_retries" IS 'current # of retries to get source code';
COMMENT ON COLUMN "contract"."next_attempt_at" IS 'if source code unavailable, next timestamp to allow scan';
COMMENT ON COLUMN "contract"."network" IS 'ETH: eth\nBSC: bsc\nPOLYGON: polygon\nBASE: base\nETH_SEPOLIA: eth_sepolia\nBSC_TEST: bsc_test\nPOLYGON_AMOY: polygon_amoy\nBASE_SEPOLIA: base_sepolia';
CREATE TABLE IF NOT EXISTS "credit" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "tier" VARCHAR(5) NOT NULL,
    "value" DOUBLE PRECISION NOT NULL  DEFAULT 1
);
COMMENT ON COLUMN "credit"."tier" IS 'FREE: free\nBASIC: basic';
CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "address" VARCHAR(255) NOT NULL UNIQUE,
    "total_credits" INT NOT NULL  DEFAULT 0,
    "remaining_credits" INT NOT NULL  DEFAULT 0
);
CREATE INDEX IF NOT EXISTS "idx_user_address_dcaffb" ON "user" ("address");
CREATE TABLE IF NOT EXISTS "app" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL,
    "type" VARCHAR(11) NOT NULL  DEFAULT 'third_party',
    "owner_id" UUID REFERENCES "user" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_app_type_8080af" ON "app" ("type");
COMMENT ON COLUMN "app"."type" IS 'FIRST_PARTY: first_party\nTHIRD_PARTY: third_party';
CREATE TABLE IF NOT EXISTS "audit" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "model" VARCHAR(255),
    "audit_type" VARCHAR(8) NOT NULL,
    "processing_time_seconds" INT,
    "status" VARCHAR(10)   DEFAULT 'waiting',
    "raw_output" TEXT,
    "app_id" UUID REFERENCES "app" ("id") ON DELETE SET NULL,
    "contract_id" UUID NOT NULL REFERENCES "contract" ("id") ON DELETE CASCADE,
    "user_id" UUID REFERENCES "user" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_audit_user_id_a201a6" ON "audit" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_audit_user_id_e9ee8e" ON "audit" ("user_id", "audit_type", "contract_id");
CREATE INDEX IF NOT EXISTS "idx_audit_user_id_8e4fb6" ON "audit" ("user_id", "audit_type");
CREATE INDEX IF NOT EXISTS "idx_audit_audit_t_592cbe" ON "audit" ("audit_type", "contract_id");
COMMENT ON COLUMN "audit"."audit_type" IS 'SECURITY: security\nGAS: gas';
COMMENT ON COLUMN "audit"."status" IS 'WAITING: waiting\nPROCESSING: processing\nSUCCESS: success\nFAILED: failed';
CREATE TABLE IF NOT EXISTS "auth" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "client_type" VARCHAR(4) NOT NULL  DEFAULT 'user',
    "hashed_key" VARCHAR(255) NOT NULL,
    "is_revoked" BOOL NOT NULL  DEFAULT False,
    "app_id" UUID REFERENCES "app" ("id") ON DELETE SET NULL,
    "user_id" UUID REFERENCES "user" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_auth_hashed__8b449a" ON "auth" ("hashed_key");
COMMENT ON COLUMN "auth"."client_type" IS 'USER: user\nAPP: app';
CREATE TABLE IF NOT EXISTS "finding" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "audit_type" VARCHAR(8) NOT NULL,
    "level" VARCHAR(8) NOT NULL,
    "name" TEXT,
    "explanation" TEXT,
    "recommendation" TEXT,
    "reference" TEXT,
    "is_attested" BOOL NOT NULL  DEFAULT False,
    "is_verified" BOOL NOT NULL  DEFAULT False,
    "feedback" TEXT,
    "attested_at" TIMESTAMPTZ,
    "audit_id" UUID NOT NULL REFERENCES "audit" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "finding"."audit_type" IS 'SECURITY: security\nGAS: gas';
COMMENT ON COLUMN "finding"."level" IS 'CRITICAL: critical\nHIGH: high\nMEDIUM: medium\nLOW: low';
CREATE TABLE IF NOT EXISTS "intermediate_response" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "step" VARCHAR(9) NOT NULL,
    "result" TEXT NOT NULL,
    "audit_id" UUID NOT NULL REFERENCES "audit" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "intermediate_response"."step" IS 'CANDIDATE: candidate\nREVIEWER: reviewer\nREPORTER: reporter';
CREATE TABLE IF NOT EXISTS "transaction" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "type" VARCHAR(8) NOT NULL,
    "amount" DOUBLE PRECISION NOT NULL,
    "app_id" UUID REFERENCES "app" ("id") ON DELETE SET NULL,
    "user_id" UUID REFERENCES "user" ("id") ON DELETE SET NULL
);
COMMENT ON COLUMN "transaction"."type" IS 'PURCHASE: purchase\nUSE: spend\nREFUND: refund';
CREATE TABLE IF NOT EXISTS "webhook" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "url" VARCHAR(255) NOT NULL,
    "event" VARCHAR(12) NOT NULL,
    "is_enabled" BOOL NOT NULL  DEFAULT True,
    "failure_count" INT NOT NULL  DEFAULT 0,
    "last_failure" TIMESTAMPTZ,
    "last_success" TIMESTAMPTZ,
    "next_retry" TIMESTAMPTZ,
    "app_id" UUID REFERENCES "app" ("id") ON DELETE SET NULL,
    "user_id" UUID REFERENCES "user" ("id") ON DELETE SET NULL
);
COMMENT ON COLUMN "webhook"."event" IS 'EVAL_UPDATED: eval.updated';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
