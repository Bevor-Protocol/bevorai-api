import logging
from datetime import datetime

from app.api.ai.pipeline import LlmPipeline
from app.db.models import Audit, Contract
from app.utils.enums import AppTypeEnum, AuditStatusEnum, AuditTypeEnum


async def handle_eval(audit_id: str, contract_id: str, audit_type: AuditTypeEnum):
    now = datetime.now()
    audit = await Audit.get(id=audit_id).select_related("app")
    contract = await Contract.get(id=contract_id)

    # only use pubsub for first-party applications.
    # otherwise, we can rely on webhooks or polling.
    should_publish = audit.app and audit.app.type == AppTypeEnum.FIRST_PARTY

    pipeline = LlmPipeline(
        input=contract.raw_code,
        audit=audit,
        should_publish=should_publish,
        should_write_to_db=True,
    )

    audit.model = pipeline.model
    audit.status = AuditStatusEnum.PROCESSING
    await audit.save()

    try:
        await pipeline.generate_candidates()
        await pipeline.generate_judgement()

        response = await pipeline.generate_report()

        audit.raw_output = response
        audit.status = AuditStatusEnum.SUCCESS

    except Exception as err:
        logging.error(err)
        audit.status = AuditStatusEnum.FAILED
        audit.processing_time_seconds = (datetime.now() - now).seconds
        await audit.save()
        raise err

    audit.processing_time_seconds = (datetime.now() - now).seconds
    await audit.save()

    return {"audit_id": audit_id, "audit_status": audit.status}
