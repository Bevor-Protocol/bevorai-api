import datetime
import json
import logging
from typing import Optional

import httpx
from replicate.prediction import Prediction

from app.cache import redis_client
from app.db.models import Audit
from app.pydantic.response import EvalResponse, EvalResponseData
from app.queues import queue_high
from app.utils.enums import AuditStatusEnum

from .eval import sanitize_data


async def process_webhook_replicate(
    data: Prediction,
    webhook_url: Optional[str] = None,
):

    id = data.id
    started_at = data.started_at
    completed_at = data.completed_at
    status = data.status

    status_mapper = {
        "succeeded": AuditStatusEnum.SUCCESS,
        "failed": AuditStatusEnum.FAILED,
        "canceled": AuditStatusEnum.FAILED,
    }

    audit_status = status_mapper[status]

    audit = await Audit.latest(job_id=id)

    if not audit:
        logging.error(f"Webhook received for job {id}, but no Audit object exists")
        if webhook_url:
            queue_high.enqueue(
                handle_outgoing_webhook_failure,
                webhook_url=webhook_url,
            )
        return

    started = datetime.datetime.strptime(started_at, "%Y-%m-%dT%H:%M:%S.%fZ")
    completed = datetime.datetime.strptime(completed_at, "%Y-%m-%dT%H:%M:%S.%fZ")
    processing_time = (completed - started).total_seconds()

    audit: Audit
    audit.results_status = audit_status
    audit.processing_time_seconds = processing_time

    if audit_status == AuditStatusEnum.SUCCESS:
        response_completed = ""
        for r in data.output:
            response_completed += r
        audit.results_raw_output = response_completed

    await audit.save()

    if webhook_url:
        queue_high.enqueue(
            handle_outgoing_webhook,
            audit=audit,
            webhook_url=webhook_url,
        )

    if audit.referer == "app.certaik.xyz":
        # we'll always return markdown to the client here.
        result = sanitize_data(
            raw_data=audit.results_raw_output,
            audit_type=audit.audit_type,
            as_markdown=True,
        )

        message = json.dumps(
            {
                "id": str(audit.id),
                "result": result,
            }
        )
        redis_client.publish(
            "evals",
            message,
        )


async def handle_outgoing_webhook_failure(
    webhook_url: str,
):
    response = EvalResponse(
        success=False, exists=False, error="Issue processing this response"
    )

    async with httpx.AsyncClient() as client:
        body = response.model_dump()
        await client.post(webhook_url, data=body)


async def handle_outgoing_webhook(
    audit: Audit,
    webhook_url: str,
):
    response = EvalResponse(
        success=True,
        exists=True,
    )

    data = {
        "id": str(audit.id),
        "status": audit.results_status,
        "contract_address": audit.contract_address,
        "contract_code": audit.contract_code,
        "contract_network": audit.contract_network,
    }

    response.result = EvalResponseData(**data)

    async with httpx.AsyncClient() as client:
        response.model_validate()
        body = response.model_dump()
        await client.post(webhook_url, data=body)
