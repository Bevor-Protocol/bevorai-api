from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.api.services.permission import PermissionService
from app.db.models import App, Audit, User
from app.schema.dependencies import AuthState
from app.schema.request import AppUpsertBody
from app.schema.response import AllStatsResponse, AppInfoResponse
from app.schema.shared import Timeseries
from app.utils.enums import AppTypeEnum, AuditTypeEnum, ClientTypeEnum, FindingLevelEnum


class AppService:
    async def create(self, auth: AuthState, body: AppUpsertBody) -> bool:

        app = await App.filter(owner_id=auth.user_id).first()
        if app:
            return True

        permission_service = PermissionService()
        async with in_transaction():
            app = await App.create(
                owner_id=auth.user_id, name=body.name, type=AppTypeEnum.THIRD_PARTY
            )
            await permission_service.create(
                client_type=ClientTypeEnum.APP,
                identifier=app.id,
                permissions={"can_create_api_key": True},
            )

        return True

    async def update(self, auth: AuthState, body: AppUpsertBody) -> bool:

        app = await App.filter(owner_id=auth.user_id).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this user does not an app yet",
            )
        app.name = body.name
        await app.save()

        return True

    async def get_info(self, app_id: str) -> AppInfoResponse:

        app = await App.get(id=app_id).prefetch_related("users", "audits")

        audits = app.audits
        users = app.users

        n_users = len(users)
        n_audits = len(audits)
        n_contracts = len(set(map(lambda x: x.contract_id, audits)))

        response = AppInfoResponse(
            id=app.id,
            created_at=app.created_at,
            name=app.name,
            n_users=n_users,
            n_contracts=n_contracts,
            n_audits=n_audits,
        )

        return response

    async def get_stats(self) -> AllStatsResponse:
        """
        pass an app_id if not the FIRST_PARTY app.
        """

        n_apps = await App.all().count()

        audits = await Audit.all().prefetch_related("findings")
        users = await User.all()

        users_by_date = {}
        n_users = 0
        for user in users:
            date = str(user.created_at.date())
            if date not in users_by_date:
                users_by_date[date] = 0
            users_by_date[date] += 1
            n_users += 1

        users_timeseries = sorted(
            [
                Timeseries(date=date, count=count)
                for date, count in users_by_date.items()
            ],
            key=lambda x: x.date,
        )

        audits_by_date = {}
        contract_set = set()
        gas_findings = {k.value: 0 for k in FindingLevelEnum}
        sec_findings = {k.value: 0 for k in FindingLevelEnum}
        n_audits = 0
        n_contracts = 0
        for audit in audits:
            date = str(audit.created_at.date())
            if date not in audits_by_date:
                audits_by_date[date] = 0
            contract_set.add(audit.contract_id)
            audits_by_date[date] += 1
            n_audits += 1

            for finding in audit.findings:
                match finding.audit_type:
                    case AuditTypeEnum.SECURITY:
                        sec_findings[finding.level] += 1
                    case AuditTypeEnum.GAS:
                        gas_findings[finding.level] += 1

        n_contracts = len(contract_set)
        audits_timeseries = sorted(
            [
                Timeseries(date=date, count=count)
                for date, count in audits_by_date.items()
            ],
            key=lambda x: x.date,
        )
        response = AllStatsResponse(
            n_apps=n_apps,
            n_users=n_users,
            n_contracts=n_contracts,
            n_audits=n_audits,
            findings={
                AuditTypeEnum.GAS: gas_findings,
                AuditTypeEnum.SECURITY: sec_findings,
            },
            users_timeseries=users_timeseries,
            audits_timeseries=audits_timeseries,
        )

        return response
