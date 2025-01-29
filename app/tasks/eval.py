import asyncio
import json
import logging
from datetime import datetime

from app.api.ai.pipeline import LlmPipeline
from app.cache import redis_client
from app.db.models import Audit
from app.utils.enums import AuditStatusEnum, AuditTypeEnum


async def test_get():
    logging.info("GETTING AUDIT")
    audit = await Audit.first()
    logging.info("GOT AUDIT")
    logging.info(audit.id)


async def handle_eval(job_id: str, audit_id: str, code: str, audit_type: AuditTypeEnum):
    logging.info(f"FCT CALLED {job_id}")
    now = datetime.now()
    audit = await Audit.get(id=audit_id)
    logging.info("AUDIT FETCHED")
    pipeline = LlmPipeline(input=code, audit_type=audit_type)
    await redis_client.publish(
        "evals",
        json.dumps(
            {
                "type": "eval",
                "step": "generating_candidates",
                "job_id": job_id,
                "result": None,
            }
        ),
    )

    audit.model = pipeline.model
    try:
        await pipeline.generate_candidates()
        await redis_client.publish(
            "evals",
            json.dumps(
                {
                    "type": "eval",
                    "step": "generating_judgements",
                    "job_id": job_id,
                    "result": None,
                }
            ),
        )
        logging.info("THEN HERE")
        await pipeline.generate_judgement()
        await redis_client.publish(
            "evals",
            json.dumps(
                {
                    "type": "eval",
                    "step": "generating_report",
                    "job_id": job_id,
                    "result": None,
                }
            ),
        )
        logging.info("AND HERE")
        response = await pipeline.generate_report()

        audit.results_raw_output = response
        audit.results_status = AuditStatusEnum.SUCCESS
        audit.processing_time_seconds = (datetime.now() - now).seconds

        await redis_client.publish(
            "evals",
            json.dumps(
                {"type": "eval", "step": "done", "job_id": job_id, "result": response}
            ),
        )
    except Exception as err:
        logging.error(err)
        audit.results_status = AuditStatusEnum.FAILED
        await redis_client.publish(
            "evals",
            json.dumps(
                {"type": "eval", "step": "error", "job_id": job_id, "result": None}
            ),
        )

    await audit.save()

    return {"audit_id": audit_id, "audit_status": audit.results_status}
