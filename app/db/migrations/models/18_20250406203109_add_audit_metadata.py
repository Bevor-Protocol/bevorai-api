import json
import re

from tortoise import BaseDBAsyncClient

from app.db.models import Audit, AuditMetadata
from app.utils.types.llm import OutputStructure


async def upgrade(db: BaseDBAsyncClient) -> str:
    query = """
        CREATE TABLE IF NOT EXISTS "audit_metadata" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "introduction" TEXT,
    "scope" TEXT,
    "conclusion" TEXT,
    "audit_id" UUID NOT NULL UNIQUE REFERENCES "audit" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_audit_metad_audit_i_0df71a" ON "audit_metadata" ("audit_id");"""

    await db.execute_script(query)

    audits = await Audit.all(using_db=db)

    metadatas = []
    for audit in audits:
        if not audit.raw_output:
            # I'll keep a reference to it
            metadatas.append(AuditMetadata(audit=audit))
            continue
        pattern = r"<<(.*?)>>"
        raw_data = re.sub(pattern, r"`\1`", audit.raw_output)

        pattern = r"\{.*\}"
        match = re.search(pattern, raw_data, re.DOTALL)
        if match:
            raw_data = match.group(0)

        parsed = json.loads(raw_data)

        model = OutputStructure(**parsed)

        metadatas.append(
            AuditMetadata(
                audit=audit,
                introduction=model.introduction,
                scope=model.scope,
                conclusion=model.conclusion,
            )
        )

    await AuditMetadata.bulk_create(metadatas, using_db=db)

    return """SELECT * FROM "audit_metadata" limit 1;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "audit_metadata";"""
