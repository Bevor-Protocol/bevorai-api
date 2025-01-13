from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "audit" ALTER COLUMN "user_id" DROP NOT NULL;
        ALTER TABLE "contract" RENAME COLUMN "contract_network" TO "network";
        ALTER TABLE "contract" RENAME COLUMN "contract_address" TO "address";
        ALTER TABLE "contract" RENAME COLUMN "contract_code" TO "raw_code";
        ALTER TABLE "contract" RENAME COLUMN "contract_hash" TO "hash_code";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "audit" ALTER COLUMN "user_id" SET NOT NULL;
        ALTER TABLE "contract" RENAME COLUMN "raw_code" TO "contract_code";
        ALTER TABLE "contract" RENAME COLUMN "hash_code" TO "contract_hash";
        ALTER TABLE "contract" RENAME COLUMN "address" TO "contract_address";
        ALTER TABLE "contract" RENAME COLUMN "network" TO "contract_network";"""
