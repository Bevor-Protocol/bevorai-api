from tortoise import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from app.db.models import IntermediateResponse, Prompt
from app.utils.types.enums import AuditTypeEnum

"""
Shipped the prompt table, with a proper backfill, but there was a bug that didn't
add the prompt relation for new observations.
"""


async def upgrade(db: BaseDBAsyncClient) -> str:
    await (
        IntermediateResponse.filter(step="report").using_db(db).update(step="reviewer")
    )

    intermediate_responses = (
        await IntermediateResponse.filter(prompt_id__isnull=True)
        .using_db(db)
        .select_related("audit")
    )

    # we currently only have active prompts at the time of creating this migration.
    security_prompts = await Prompt.filter(audit_type=AuditTypeEnum.SECURITY).using_db(
        db
    )
    gas_prompts = await Prompt.filter(audit_type=AuditTypeEnum.GAS).using_db(db)

    security_prompts = {prompt.tag: prompt.id for prompt in security_prompts}
    gas_prompts = {prompt.tag: prompt.id for prompt in gas_prompts}

    async with in_transaction():
        for intermediate_response in intermediate_responses:
            if intermediate_response.audit.audit_type == AuditTypeEnum.SECURITY:
                prompt_id = security_prompts.get(intermediate_response.step)
            else:
                prompt_id = gas_prompts.get(intermediate_response.step)

            if prompt_id:
                intermediate_response.prompt_id = prompt_id
                await intermediate_response.save(using_db=db)

    return """
        SELECT * FROM intermediate_response limit 1;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        SELECT * FROM intermediate_response limit 1;"""
