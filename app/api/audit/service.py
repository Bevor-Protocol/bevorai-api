from collections import defaultdict
import math
from logfire.propagate import get_context

from arq import create_pool
from fastapi import HTTPException, status
from tortoise.timezone import now

from app.config import redis_settings
from app.db.models import Audit, AuditMetadata, Contract, Finding
from app.utils.types.models import AuditSchema
from app.utils.types.relations import AuditRelation, AuditWithFindingsRelation
from app.utils.types.shared import AuthState
from app.utils.templates.gas import gas_template
from app.utils.templates.security import security_template
from app.utils.types.enums import AuditTypeEnum, FindingLevelEnum, RoleEnum

from .interface import (
    AuditIndex,
    AuditResponse,
    AuditsResponse,
    EvalBody,
    FeedbackBody,
    FilterParams,
    GetAuditStatusResponse,
)


class AuditService:
    template_map: dict[AuditTypeEnum, str] = {
        AuditTypeEnum.GAS: gas_template,
        AuditTypeEnum.SECURITY: security_template,
    }

    async def get_audits(self, auth: AuthState, query: FilterParams) -> AuditsResponse:
        limit = query.page_size
        offset = query.page * limit

        filter = {}
        if query.status:
            filter["status"] = query.status
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
            return AuditsResponse(more=False, total_pages=total_pages)

        audits = (
            await audit_query.order_by("-created_at")
            .offset(offset)
            .limit(limit + 1)
            .select_related("user", "contract")
        )

        audits_trimmed = audits[:-1] if len(audits) > limit else audits

        data = []
        for i, audit in enumerate(audits_trimmed):
            response = AuditIndex(
                **AuditRelation.model_validate(audit).model_dump(), n=i + offset
            )
            data.append(response)

        return AuditsResponse(
            results=data, more=len(audits) > query.page_size, total_pages=total_pages
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
            .prefetch_related("findings", "audit_metadata")
        )

        result = self._parse_branded_markdown(audit=audit)

        return AuditResponse(
            **AuditWithFindingsRelation.model_validate(audit).model_dump(),
            result=result,
        )

    async def get_status(self, auth: AuthState, id: str) -> GetAuditStatusResponse:
        obj_filter = {"id": id}
        if auth.role == RoleEnum.APP:
            obj_filter["app_id"] = auth.app_id
        if auth.role == RoleEnum.USER:
            obj_filter["user_id"] = auth.user_id

        audit = await Audit.get(**obj_filter).prefetch_related("intermediate_responses")

        response = GetAuditStatusResponse(
            **AuditSchema.model_validate(audit).model_dump(),
            steps=audit.intermediate_responses,
        )

        return response

    async def submit_feedback(
        self, data: FeedbackBody, auth: AuthState, id: str
    ) -> None:
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

    def _parse_branded_markdown(self, audit: Audit) -> str | None:
        """parse audit and findings into markdown format"""
        template_use = self.template_map[audit.audit_type]

        metadata: AuditMetadata | None = audit.audit_metadata
        if not metadata:
            return

        formatter = {
            "address": audit.contract.address,
            "date": audit.created_at.strftime("%Y-%m-%d"),
            "introduction": metadata.introduction,  # audit-level intro
            "scope": metadata.scope,  # audit-level scope
            "conclusion": metadata.conclusion,  # audit-level conclusion
        }

        findings_dict = defaultdict(str)
        for finding in audit.findings:
            key = f"findings_{finding.level.value}"

            findings_dict[key] += f"**{finding.name}**\n"
            findings_dict[key] += f"- **Explanation**: {finding.explanation}\n"
            findings_dict[key] += f"- **Recommendation**: {finding.recommendation}\n"
            findings_dict[key] += f"- **Code Reference**: {finding.reference}\n\n"

        for level in FindingLevelEnum:
            key = f"findings_{level.value}"
            if key not in findings_dict:
                findings_dict[key] = "None Identified"
            else:
                findings_dict[key] = findings_dict[key].strip()

        return template_use.format(**formatter, **findings_dict)

    async def initiate_audit(self, auth: AuthState, data: EvalBody) -> Audit:
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
        log_context = get_context()
        await redis_pool.enqueue_job(
            "process_eval",
            _job_id=str(audit.id),
            trace=log_context,
        )

        return audit
