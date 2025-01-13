import httpx

from app.pydantic.response import WebhookResponse, WebhookResponseData
from app.utils.enums import AuditStatusEnum


async def handle_outgoing_webhook(
    audit_id: str,
    audit_status: AuditStatusEnum,
    webhook_url: str,
):
    response = WebhookResponse(
        success=True,
    )

    data = {
        "id": audit_id,
        "status": audit_status,
    }

    response.result = WebhookResponseData(**data)

    async with httpx.AsyncClient() as client:
        body = response.model_dump()
        await client.post(webhook_url, json=body)
