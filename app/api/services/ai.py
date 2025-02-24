import json
import re

from arq import create_pool
from fastapi import HTTPException

from app.config import redis_settings
from app.db.models import Audit, Contract
from app.lib.gas import versions as gas_versions
from app.lib.security import versions as sec_versions
from app.schema.dependencies import AuthState
from app.schema.request import EvalBody
from app.schema.response import CreateEvalResponse
from app.utils.enums import AuditStatusEnum, AuditTypeEnum

# from app.worker import process_eval


class AiService:

    def sanitize_data(self, audit: Audit, as_markdown: bool):
        # sanitizing backslashes/escapes for code blocks
        pattern = r"<<(.*?)>>"

        # this parsing should not be required, but we'll include it for safety
        raw_data = re.sub(pattern, r"`\1`", audit.raw_output)

        # corrects for occassional leading non-json text...
        pattern = r"\{.*\}"
        match = re.search(pattern, raw_data, re.DOTALL)
        if match:
            raw_data = match.group(0)

        parsed = json.loads(raw_data)

        if as_markdown:
            parsed = self.parse_branded_markdown(audit=audit, findings=parsed)

        return parsed

    def parse_branded_markdown(self, audit: Audit, findings: dict):
        # See if i can cast it back to the expected Pydantic struct.
        version_use = (
            gas_versions if audit.audit_type == AuditTypeEnum.GAS else sec_versions
        )
        version = version_use[audit.version]
        markdown = version["markdown"]
        result = markdown

        formatter = {
            "address": audit.contract.address,
            "date": audit.created_at.strftime("%Y-%m-%d"),
            "introduction": findings["introduction"],
            "scope": findings["scope"],
            "conclusion": findings["conclusion"],
        }

        pattern = r"<<(.*?)>>"

        for k, v in findings["findings"].items():
            key = f"findings_{k}"
            finding_str = ""
            if not v:
                finding_str = "None Identified"
            else:
                for finding in v:
                    name = re.sub(pattern, r"`\1`", finding["name"])
                    explanation = re.sub(pattern, r"`\1`", finding["explanation"])
                    recommendation = re.sub(pattern, r"`\1`", finding["recommendation"])
                    reference = re.sub(pattern, r"`\1`", finding["reference"])

                    finding_str += f"**{name}**\n"
                    finding_str += f"- **Explanation**: {explanation}\n"
                    finding_str += f"- **Recommendation**: {recommendation}\n"
                    finding_str += f"- **Code Reference**: {reference}\n\n"

            formatter[key] = finding_str.strip()

        return result.format(**formatter)

    async def process_evaluation(
        self, auth: AuthState, data: EvalBody
    ) -> CreateEvalResponse:
        if not await Contract.exists(id=data.contract_id):
            raise HTTPException(
                status_code=404,
                detail=(
                    "you must provide a valid internal contract_id, "
                    "call /blockchain/scan first"
                ),
            )

        audit_type = data.audit_type
        # webhook_url = data.webhook_url

        audit = await Audit.create(
            contract_id=data.contract_id,
            app_id=auth.app_id,
            user_id=auth.user_id,
            audit_type=audit_type,
        )

        redis_pool = await create_pool(redis_settings)

        # the job_id is guaranteed to be unique, make it align with the audit.id
        # for simplicitly.
        await redis_pool.enqueue_job(
            "process_eval",
            _job_id=str(audit.id),
        )

        return CreateEvalResponse(id=audit.id, status=AuditStatusEnum.WAITING)
