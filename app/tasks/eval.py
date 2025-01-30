import json
import logging
from datetime import datetime

from app.api.ai.pipeline import LlmPipeline
from app.cache import redis_client
from app.db.models import Audit
from app.utils.enums import AppTypeEnum, AuditStatusEnum, AuditTypeEnum


async def test_get():
    logging.info("GETTING AUDIT")
    audit = await Audit.first()
    logging.info("GOT AUDIT")
    logging.info(audit.id)


async def publish_event(job_id: str, step: str):
    await redis_client.publish(
        "evals",
        json.dumps(
            {
                "type": "eval",
                "step": step,
                "job_id": job_id,
            }
        ),
    )


async def handle_eval(job_id: str, audit_id: str, code: str, audit_type: AuditTypeEnum):
    now = datetime.now()
    audit = await Audit.get(id=audit_id).select_related("app")

    # only use pubsub for first-party applications.
    # otherwise, we can rely on webhooks or polling.
    should_publish = audit.app and audit.app.type == AppTypeEnum.FIRST_PARTY

    pipeline = LlmPipeline(input=code, audit_type=audit_type)

    if should_publish:
        await publish_event(job_id=job_id, step="generating_candidates")

    audit.model = pipeline.model
    audit.results_status = AuditStatusEnum.PROCESSING
    await audit.save()
    try:
        await pipeline.generate_candidates()
        if should_publish:
            await publish_event(job_id=job_id, step="generating_judgements")

        await pipeline.generate_judgement()
        if should_publish:
            await publish_event(job_id=job_id, step="generating_report")

        response = await pipeline.generate_report()

        audit.results_raw_output = response
        audit.results_status = AuditStatusEnum.SUCCESS
        audit.processing_time_seconds = (datetime.now() - now).seconds

        if should_publish:
            await publish_event(job_id=job_id, step="done")

    except Exception as err:
        logging.error(err)
        audit.results_status = AuditStatusEnum.FAILED
        if should_publish:
            await publish_event(job_id=job_id, step="error")

    await audit.save()

    return {"audit_id": audit_id, "audit_status": audit.results_status}
