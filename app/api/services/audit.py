import math

from fastapi import HTTPException, status
from tortoise.timezone import now

from app.api.services.ai import AiService
from app.db.models import App, Audit, Contract, Finding, User
from app.schema.dependencies import AuthState
from app.schema.request import FeedbackBody, FilterParams
from app.schema.response import (
    AnalyticsAudit,
    AnalyticsContract,
    AnalyticsResponse,
    GetAuditResponse,
    StatsResponse,
    _Audit,
    _Contract,
    _Finding,
    _User,
)
from app.utils.enums import (
    AuditTypeEnum,
    AuthScopeEnum,
    ClientTypeEnum,
    FindingLevelEnum,
)


class AuditService:

    async def get_audits(
        self, auth: AuthState, query: FilterParams
    ) -> AnalyticsResponse:

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
            return AnalyticsResponse(results=[], more=False, total_pages=total_pages)

        results = (
            await audit_query.order_by("-created_at")
            .offset(offset)
            .limit(limit + 1)
            .values(
                "id",
                "created_at",
                "app_id",
                "user__address",
                "audit_type",
                "status",
                "contract__id",
                "contract__method",
                "contract__address",
                "contract__network",
            )
        )

        results_trimmed = results[:-1] if len(results) > limit else results

        data = []
        for i, result in enumerate(results_trimmed):
            contract = AnalyticsContract(
                id=result["contract__id"],
                method=result["contract__method"],
                address=result["contract__address"],
                network=result["contract__network"],
            )
            response = AnalyticsAudit(
                n=i + offset,
                id=result["id"],
                created_at=result["created_at"],
                app_id=result["app_id"],
                user_id=result["user__address"],
                audit_type=result["audit_type"],
                status=result["status"],
                contract=contract,
            )
            data.append(response)

        return AnalyticsResponse(
            results=data, more=len(results) > query.page_size, total_pages=total_pages
        )

    async def get_stats(self) -> StatsResponse:
        n_audits = 0
        n_contracts = await Contract.all().count()
        n_users = await User.all().count()
        n_apps = await App.all().count()

        n_audits = await Audit.all().count()
        findings = await Finding.all()

        gas_findings = {k.value: 0 for k in FindingLevelEnum}
        sec_findings = {k.value: 0 for k in FindingLevelEnum}

        for finding in findings:
            match finding.audit_type:
                case AuditTypeEnum.SECURITY:
                    sec_findings[finding.level] += 1
                case AuditTypeEnum.GAS:
                    gas_findings[finding.level] += 1

        response = StatsResponse(
            n_apps=n_apps,
            n_users=n_users,
            n_contracts=n_contracts,
            n_audits=n_audits,
            findings={
                AuditTypeEnum.GAS: gas_findings,
                AuditTypeEnum.SECURITY: sec_findings,
            },
        )

        return response

    async def get_audit(self, auth: AuthState, id: str) -> GetAuditResponse:
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

        findings = []
        finding: Finding
        for finding in audit.findings:
            findings.append(
                _Finding(
                    id=str(finding.id),
                    level=finding.level,
                    name=finding.name,
                    explanation=finding.explanation,
                    recommendation=finding.recommendation,
                    reference=finding.reference,
                    is_attested=finding.is_attested,
                    is_verified=finding.is_verified,
                    feedback=finding.feedback,
                )
            )

        return GetAuditResponse(
            contract=_Contract(
                address=audit.contract.address,
                network=audit.contract.network,
                code=audit.contract.raw_code,
            ),
            user=_User(
                id=str(audit.user.id),
                address=audit.user.address,
            ),
            audit=_Audit(
                status=audit.status,
                version=audit.version,
                audit_type=audit.audit_type,
                result=result,
            ),
            findings=findings,
        )

    async def submit_feedback(self, data: FeedbackBody, auth: AuthState) -> bool:

        finding = await Finding.get(id=data.id).select_related("audit")

        user_id = finding.audit.user_id
        app_id = finding.audit.app_id

        if auth.client_type == ClientTypeEnum.USER:
            if (not user_id) or (user_id != auth.user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="user did not create this finding",
                )
        if auth.client_type == ClientTypeEnum.APP:
            if auth.scope != AuthScopeEnum.ADMIN:
                if (not app_id) or (app_id != auth.app_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="app did not create this finding",
                    )

        finding.is_attested = True
        finding.is_verified = data.verified
        finding.feedback = data.feedback
        finding.attested_at = now()

        await finding.save()

        return True
