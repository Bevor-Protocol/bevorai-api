import math

from fastapi import HTTPException, status
from tortoise.timezone import now

from app.api.services.ai import AiService
from app.db.models import Audit, Finding
from app.schema.audit import AuditStepPydantic
from app.schema.dependencies import AuthState
from app.schema.request import FeedbackBody, FilterParams
from app.schema.response import (
    AuditMetadata,
    AuditResponse,
    AuditsResponse,
    GetAuditStatusResponse,
)
from app.utils.enums import AuthScopeEnum, ClientTypeEnum
from app.utils.model_parser import (
    cast_contract,
    cast_contract_with_code,
    cast_finding,
    cast_user,
)


class AuditService:

    async def get_audits(self, auth: AuthState, query: FilterParams) -> AuditsResponse:

        limit = query.page_size
        offset = query.page * limit

        filter = {}
        if query.search:
            filter["status"] = query.search
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
        if auth.client_type == ClientTypeEnum.APP:
            if auth.scope != AuthScopeEnum.ADMIN:
                filter["app_id"] = auth.app_id
        else:
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
            contract = cast_contract(result.contract)
            user = cast_user(result.user)
            response = AuditMetadata(
                id=result.id,
                created_at=result.created_at,
                n=i + offset,
                audit_type=result.audit_type,
                status=result.status,
                user=user,
                contract=contract,
            )
            data.append(response)

        return AuditsResponse(
            results=data, more=len(results) > query.page_size, total_pages=total_pages
        )

    async def get_audit(self, auth: AuthState, id: str) -> AuditResponse:
        obj_filter = {"id": id}
        if auth.client_type == ClientTypeEnum.USER:
            obj_filter["user_id"] = auth.user_id
        else:
            if auth.scope != AuthScopeEnum.ADMIN:
                obj_filter["app_id"] = auth.app_id

        audit = (
            await Audit.get(**obj_filter)
            .select_related("contract", "user")
            .prefetch_related("findings")
        )

        result = None
        if audit.raw_output:
            ai_service = AiService()
            result = ai_service.sanitize_data(audit=audit, as_markdown=True)

        findings = list(map(cast_finding, audit.findings))
        contract = cast_contract_with_code(audit.contract)
        user = cast_user(audit.user)

        return AuditResponse(
            id=audit.id,
            created_at=audit.created_at,
            status=audit.status,
            version=audit.version,
            audit_type=audit.audit_type,
            processing_time_seconds=audit.processing_time_seconds,
            result=result,
            findings=findings,
            contract=contract,
            user=user,
        )

    async def get_status(self, auth: AuthState, id: str) -> GetAuditStatusResponse:
        obj_filter = {"id": id}
        if auth.client_type == ClientTypeEnum.USER:
            obj_filter["user_id"] = auth.user_id
        else:
            if auth.scope != AuthScopeEnum.ADMIN:
                obj_filter["app_id"] = auth.app_id

        audit = await Audit.get(**obj_filter).prefetch_related("intermediate_responses")

        steps = []
        for step in audit.intermediate_responses:
            steps.append(
                AuditStepPydantic(
                    step=step.step,
                    status=step.status,
                    processing_time_seconds=step.processing_time_seconds,
                )
            )

        response = GetAuditStatusResponse(status=audit.status, steps=steps)

        return response

    async def submit_feedback(self, data: FeedbackBody, auth: AuthState, id=id) -> bool:

        finding = await Finding.get(id=id).select_related("audit")

        user_id = finding.audit.user_id
        app_id = finding.audit.app_id

        if auth.client_type == ClientTypeEnum.USER:
            if (not user_id) or (user_id != auth.user_id):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="user did not create this finding",
                )
        if auth.client_type == ClientTypeEnum.APP:
            if auth.scope != AuthScopeEnum.ADMIN:
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
