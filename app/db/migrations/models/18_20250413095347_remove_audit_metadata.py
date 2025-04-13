import json
import re

from tortoise import BaseDBAsyncClient

from app.db.models import Audit
from app.utils.types.llm import OutputStructure


async def upgrade(db: BaseDBAsyncClient) -> str:
    query = """
        ALTER TABLE "audit" ADD "conclusion" TEXT;
        ALTER TABLE "audit" ADD "input_tokens" INT DEFAULT 0;
        ALTER TABLE "audit" ADD "introduction" TEXT;
        ALTER TABLE "audit" ADD "scope" TEXT;
        ALTER TABLE "audit" ADD "output_tokens" INT DEFAULT 0;"""

    await db.execute_script(query)

    audits = await Audit.all(using_db=db)

    for audit in audits:
        pattern = r"<<(.*?)>>"
        raw_data = re.sub(pattern, r"`\1`", audit.raw_output)

        pattern = r"\{.*\}"
        match = re.search(pattern, raw_data, re.DOTALL)
        if match:
            raw_data = match.group(0)

        parsed = json.loads(raw_data)

        model = OutputStructure(**parsed)

        audit.scope = model.scope
        audit.introduction = model.introduction
        audit.conclusion = model.conclusion

        await audit.save()


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "audit" DROP COLUMN "conclusion";
        ALTER TABLE "audit" DROP COLUMN "input_tokens";
        ALTER TABLE "audit" DROP COLUMN "introduction";
        ALTER TABLE "audit" DROP COLUMN "scope";
        ALTER TABLE "audit" DROP COLUMN "output_tokens";"""
