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
    "next_attempt" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "contract_address" VARCHAR(255),
    "contract_network" VARCHAR(12),
    "contract_code" TEXT,
    "contract_hash" VARCHAR(255)
);
COMMENT ON COLUMN "contract"."method" IS 'UPLOAD: upload\nSCAN: scan\nCRON: cron';
COMMENT ON COLUMN "contract"."is_available" IS 'if via cron, whether source code is available';
COMMENT ON COLUMN "contract"."n_retries" IS 'current # of retries to get source code';
COMMENT ON COLUMN "contract"."next_attempt" IS 'if source code unavailable, next timestamp to allow scan';
COMMENT ON COLUMN "contract"."contract_network" IS 'ETH: eth\nBSC: bsc\nPOLYGON: polygon\nBASE: base\nETH_SEPOLIA: eth_sepolia\nBSC_TEST: bsc_test\nPOLYGON_AMOY: polygon_amoy\nBASE_SEPOLIA: base_sepolia';
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
CREATE TABLE IF NOT EXISTS "app" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL,
    "type" VARCHAR(11) NOT NULL  DEFAULT 'third_party',
    "owner_id" UUID REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "app"."type" IS 'FIRST_PARTY: first_party\nTHIRD_PARTY: third_party';
CREATE TABLE IF NOT EXISTS "audit" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "job_id" VARCHAR(255) NOT NULL UNIQUE,
    "prompt_version" INT NOT NULL,
    "model" VARCHAR(255) NOT NULL,
    "audit_type" VARCHAR(8) NOT NULL,
    "processing_time_seconds" INT,
    "results_status" VARCHAR(7)   DEFAULT 'waiting',
    "results_raw_output" TEXT,
    "app_id" UUID REFERENCES "app" ("id") ON DELETE CASCADE,
    "contract_id" UUID NOT NULL REFERENCES "contract" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "audit"."audit_type" IS 'SECURITY: security\nGAS: gas';
COMMENT ON COLUMN "audit"."results_status" IS 'WAITING: waiting\nSUCCESS: success\nFAILED: failed';
CREATE TABLE IF NOT EXISTS "auth" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "client_type" VARCHAR(4) NOT NULL  DEFAULT 'user',
    "hashed_key" VARCHAR(255) NOT NULL,
    "is_revoked" BOOL NOT NULL  DEFAULT False,
    "app_id" UUID REFERENCES "app" ("id") ON DELETE CASCADE,
    "user_id" UUID REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "auth"."client_type" IS 'USER: user\nAPP: app';
CREATE TABLE IF NOT EXISTS "transaction" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "type" VARCHAR(8) NOT NULL,
    "amount" DOUBLE PRECISION NOT NULL,
    "app_id" UUID REFERENCES "app" ("id") ON DELETE CASCADE,
    "user_id" UUID REFERENCES "user" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "transaction"."type" IS 'PURCHASE: purchase\nUSE: spend\nREFUND: refund';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
