from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "audit" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "job_id" VARCHAR(255) NOT NULL UNIQUE,
    "user_id" VARCHAR(255),
    "prompt_version" INT NOT NULL,
    "contract_address" VARCHAR(255),
    "contract_network" VARCHAR(7),
    "contract_code" TEXT NOT NULL,
    "audit_type" VARCHAR(8) NOT NULL,
    "processing_time_seconds" INT,
    "results_status" VARCHAR(7)   DEFAULT 'waiting',
    "results_raw_output" TEXT
);
COMMENT ON COLUMN "audit"."contract_network" IS 'TESTNET: TESTNET\nMAINNET: MAINNET';
COMMENT ON COLUMN "audit"."audit_type" IS 'SECURITY: security\nGAS: gas';
COMMENT ON COLUMN "audit"."results_status" IS 'WAITING: waiting\nSUCCESS: success\nFAILED: failed';
CREATE TABLE IF NOT EXISTS "contract" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "contract_address" VARCHAR(255) NOT NULL,
    "contract_network" VARCHAR(7),
    "contract_code" TEXT NOT NULL
);
COMMENT ON COLUMN "contract"."contract_network" IS 'TESTNET: TESTNET\nMAINNET: MAINNET';
CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "address" VARCHAR(42) NOT NULL UNIQUE,
    "nonce" VARCHAR(32),
    "last_login" TIMESTAMPTZ,
    "is_active" BOOL NOT NULL  DEFAULT True
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
