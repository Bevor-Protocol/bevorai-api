from tortoise import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from app.db.models import Audit, IntermediateResponse, Prompt
from app.utils.backfill.prompts.gas import candidates as gas_candidates
from app.utils.backfill.prompts.security import candidates as sec_candidates
from app.utils.types.enums import AuditTypeEnum


async def upgrade(db: BaseDBAsyncClient) -> str:
    query = """
        ALTER TABLE "audit" DROP COLUMN "version";
        ALTER TABLE "intermediate_response" ADD "prompt_id" UUID;
        CREATE TABLE IF NOT EXISTS "prompt" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "audit_type" VARCHAR(8) NOT NULL,
    "tag" VARCHAR(50) NOT NULL,
    "version" VARCHAR(20) NOT NULL,
    "content" TEXT NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True
);
CREATE INDEX IF NOT EXISTS "idx_prompt_audit_t_fb5c65" ON "prompt" ("audit_type");
CREATE INDEX IF NOT EXISTS "idx_prompt_audit_t_7c4b51" ON "prompt" ("audit_type", "tag");
COMMENT ON COLUMN "prompt"."audit_type" IS 'SECURITY: security\nGAS: gas';
        DROP TABLE IF EXISTS "webhook";
        ALTER TABLE "intermediate_response" ADD CONSTRAINT "fk_intermed_prompt_4ab0edfd" FOREIGN KEY ("prompt_id") REFERENCES "prompt" ("id") ON DELETE SET NULL;"""

    await db.execute_script(query)

    n_audits = await Audit.all().count()

    if not n_audits:
        return """SELECT * FROM "prompt" limit 1;"""

    async with in_transaction():
        sec_reviewer = sec_candidates.pop("reviewer")
        for tag, prompt in sec_candidates.items():
            prompt_instance = await Prompt.create(
                audit_type=AuditTypeEnum.SECURITY,
                tag=tag,
                version="0.1",
                content=prompt,
                is_active=True,
                using_db=db,
            )

            await (
                IntermediateResponse.filter(step=tag)
                .using_db(db)
                .update(
                    prompt_id=prompt_instance.id,
                )
            )

        prompt_instance = await Prompt.create(
            audit_type=AuditTypeEnum.SECURITY,
            tag="reviewer",
            version="0.1",
            content=sec_reviewer,
            is_active=True,
            using_db=db,
        )

        audits = (
            await Audit.filter(audit_type=AuditTypeEnum.SECURITY)
            .using_db(db)
            .prefetch_related("intermediate_responses")
        )
        for audit in audits:
            for intermediate_response in audit.intermediate_responses:
                if intermediate_response.step == "reviewer":
                    intermediate_response.prompt_id = prompt_instance.id
                    await intermediate_response.save()

        gas_reviewer = gas_candidates.pop("reviewer")
        for tag, prompt in gas_candidates.items():
            prompt_instance = await Prompt.create(
                audit_type=AuditTypeEnum.GAS,
                tag=tag,
                version="0.1",
                content=prompt,
                is_active=True,
                using_db=db,
            )
            await (
                IntermediateResponse.filter(step=tag)
                .using_db(db)
                .update(prompt_id=prompt_instance.id)
            )

        prompt_instance = await Prompt.create(
            audit_type=AuditTypeEnum.GAS,
            tag="reviewer",
            version="0.1",
            content=gas_reviewer,
            is_active=True,
            using_db=db,
        )

        audits = (
            await Audit.filter(audit_type=AuditTypeEnum.GAS)
            .using_db(db)
            .prefetch_related("intermediate_responses")
        )
        for audit in audits:
            for intermediate_response in audit.intermediate_responses:
                if intermediate_response.step == "reviewer":
                    intermediate_response.prompt_id = prompt_instance.id
                    await intermediate_response.save()

    return """SELECT * FROM "prompt" limit 1;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "intermediate_response" DROP CONSTRAINT IF EXISTS "fk_intermed_prompt_4ab0edfd";
        ALTER TABLE "intermediate_response" DROP COLUMN "prompt_id";
        ALTER TABLE "audit" ADD "version" VARCHAR(20)   DEFAULT 'v1';
        DROP TABLE IF EXISTS "prompt";"""
