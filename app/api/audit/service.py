import json
import math
import re

from arq import create_pool
from fastapi import HTTPException, status
from tortoise.timezone import now

from app.config import redis_settings
from app.db.models import Audit, Contract, Finding
from app.utils.types.shared import AuthState
from app.utils.types.models import (
    IntermediateResponseSchema,
)
from app.utils.templates.gas import gas_template
from app.utils.templates.security import security_template
from app.utils.types.enums import AuditTypeEnum, RoleEnum

from .interface import (
    AuditMetadata,
    AuditResponse,
    AuditsResponse,
    CreateEvalResponse,
    EvalBody,
    FeedbackBody,
    FilterParams,
    GetAuditStatusResponse,
)


class AuditService:
    async def get_audits(self, auth: AuthState, query: FilterParams) -> AuditsResponse:
        limit = query.page_size
        offset = query.page * limit

        filter = {}
        if query.status:
            filter["status"] = query.status
        if query.search:
            filter["raw_output__icontains"] = query.search
        if query.audit_type:
            filter["audit_type__in"] = query.audit_type
        if query.network:
            filter["contract__network__in"] = query.network
        if query.contract_address:
            filter["contract__address__icontains"] = query.contract_address
        if query.user_address:
            filter["user__address__icontains"] = query.user_address
        if query.user_id:
            filter["user_id"] = query.user_id

        # FIRST_PARTY apps can view all. THIRD_PARTY apps can only view those created
        # through their app. Users can only view their own audits. If accessed via our
        # frontend all are viewable.
        if auth.role == RoleEnum.APP:
            filter["app_id"] = auth.app_id
        if auth.role == RoleEnum.USER:
            filter["user_id"] = auth.user_id

        audit_query = Audit.filter(**filter)

        total = await audit_query.count()

        total_pages = math.ceil(total / limit)

        if total <= offset:
            return AuditsResponse(results=[], more=False, total_pages=total_pages)

        results = (
            await audit_query.order_by("-created_at")
            .offset(offset)
            .limit(limit + 1)
            .select_related("user", "contract")
        )

        results_trimmed = results[:-1] if len(results) > limit else results

        data = []
        for i, result in enumerate(results_trimmed):
            response = AuditMetadata(
                id=result.id,
                created_at=result.created_at,
                n=i + offset,
                audit_type=result.audit_type,
                status=result.status,
                user=result.user,
                contract=result.contract,
            )
            data.append(response)

        return AuditsResponse(
            results=data, more=len(results) > query.page_size, total_pages=total_pages
        )

    async def get_audit(self, auth: AuthState, id: str) -> AuditResponse:
        obj_filter = {"id": id}

        if auth.role == RoleEnum.APP:
            obj_filter["app_id"] = auth.app_id
        if auth.role == RoleEnum.USER:
            obj_filter["user_id"] = auth.user_id

        audit = (
            await Audit.get(**obj_filter)
            .select_related("contract", "user")
            .prefetch_related("findings")
        )

        result = None
        if audit.raw_output:
            result = self.sanitize_data(audit=audit, as_markdown=True)

        return AuditResponse(
            id=audit.id,
            created_at=audit.created_at,
            status=audit.status,
            audit_type=audit.audit_type,
            processing_time_seconds=audit.processing_time_seconds,
            result=result,
            findings=audit.findings,
            contract=audit.contract,
            user=audit.user,
        )

    async def get_status(self, auth: AuthState, id: str) -> GetAuditStatusResponse:
        obj_filter = {"id": id}
        if auth.role == RoleEnum.APP:
            obj_filter["app_id"] = auth.app_id
        if auth.role == RoleEnum.USER:
            obj_filter["user_id"] = auth.user_id

        audit = await Audit.get(**obj_filter).prefetch_related("intermediate_responses")

        steps = []
        for step in audit.intermediate_responses:
            steps.append(IntermediateResponseSchema.from_tortoise(step))

        response = GetAuditStatusResponse(status=audit.status, steps=steps)

        return response

    async def submit_feedback(
        self, data: FeedbackBody, auth: AuthState, id: str
    ) -> bool:
        finding = await Finding.get(id=id).select_related("audit")

        user_id = finding.audit.user_id
        app_id = finding.audit.app_id

        if auth.role == RoleEnum.USER:
            if (not user_id) or (user_id != auth.user_id):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="user did not create this finding",
                )
        if auth.role == RoleEnum.APP:
            if (not app_id) or (app_id != auth.app_id):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="app did not create this finding",
                )

        finding.is_attested = True
        finding.is_verified = data.verified
        finding.feedback = data.feedback
        finding.attested_at = now()

        await finding.save()

        return True

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

    def parse_branded_markdown(self, audit: Audit, findings: dict) -> str:
        # See if i can cast it back to the expected Pydantic struct.
        template_use = (
            gas_template if audit.audit_type == AuditTypeEnum.GAS else security_template
        )
        result = template_use

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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "you must provide a valid internal contract_id, "
                    "call POST /contract first"
                ),
            )

        audit_type = data.audit_type

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

        return CreateEvalResponse(id=audit.id, status=audit.status)
