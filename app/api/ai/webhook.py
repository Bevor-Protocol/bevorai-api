import json
import logging
from typing import Optional

from app.cache import redis_client
from app.db.models import Audit
from app.utils.enums import AppTypeEnum, AuditStatusEnum
from app.utils.helpers import parse_datetime
from app.worker import process_webhook

from .eval import sanitize_data

# async def process_webhook_replicate(
#     data: Prediction,
#     webhook_url: Optional[str] = None,
# ):

#     id = data.id
#     started_at = data.started_at
#     completed_at = data.completed_at
#     status = data.status

#     logging.info(f"WEBHOOK HIT for job {id}")

#     status_mapper = {
#         "succeeded": AuditStatusEnum.SUCCESS,
#         "failed": AuditStatusEnum.FAILED,
#         "canceled": AuditStatusEnum.FAILED,
#     }

#     audit_status = status_mapper[status]

#     audit = await Audit.filter(job_id=id).select_related("app").first()

#     # if not audit:
#     #     logging.error(f"Webhook received for job {id}, but no Audit object exists")
#     #     if webhook_url:
#     #         queue_high.enqueue(
#     #             handle_outgoing_webhook_failure,
#     #             webhook_url=webhook_url,
#     #         )
#     #     return

#     started = parse_datetime(started_at)
#     completed = parse_datetime(completed_at)
#     processing_time = (completed - started).total_seconds()

#     audit.status = audit_status
#     audit.processing_time_seconds = processing_time

#     if audit_status == AuditStatusEnum.SUCCESS:
#         response_completed = ""
#         for r in data.output:
#             response_completed += r
#         audit.raw_output = response_completed

#     audit.status = audit_status
#     await audit.save()

#     if webhook_url:
#         process_webhook.send(
#             audit_id=str(audit.id),
#             audit_status=audit.status,
#             webhook_url=webhook_url,
#         )

#     if audit.app:
#         # If sourced from a first party app.
#         if audit.app.type == AppTypeEnum.FIRST_PARTY:
#             result = sanitize_data(
#                 raw_data=audit.raw_output,
#                 audit_type=audit.audit_type,
#                 as_markdown=True,
#             )

#             message = json.dumps(
#                 {
#                     "id": str(audit.id),
#                     "result": result,
#                 }
#             )
#             redis_client.publish(
#                 "evals",
#                 message,
#             )
