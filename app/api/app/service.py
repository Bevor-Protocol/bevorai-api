from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist
from tortoise.transactions import in_transaction

from app.api.permission.service import PermissionService
from app.db.models import App, Audit, User
from app.utils.types.shared import AuthState
from app.utils.types.shared import Timeseries
from app.utils.types.enums import (
    AppTypeEnum,
    AuditTypeEnum,
    ClientTypeEnum,
    FindingLevelEnum,
    PermissionEnum,
)

from .interface import AllStatsResponse, AppInfoResponse, AppUpsertBody


class AppService:
    async def create(self, auth: AuthState, body: AppUpsertBody) -> None:
        app = await App.filter(owner_id=auth.user_id).first()
        if app:
            return

        permission_service = PermissionService()

        has_permission = await permission_service.has_permission(
            client_type=ClientTypeEnum.USER,
            identifier=auth.user_id,
            permission=[PermissionEnum.CREATE_APP],
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="wrong permissions to create an app",
            )

        async with in_transaction():
            app = await App.create(
                owner_id=auth.user_id, name=body.name, type=AppTypeEnum.THIRD_PARTY
            )
            await permission_service.create(
                client_type=ClientTypeEnum.APP,
                identifier=app.id,
                permissions={"can_create_api_key": True},
            )

    async def update(self, auth: AuthState, body: AppUpsertBody) -> None:
        app = await App.filter(owner_id=auth.user_id).first()
        if not app:
            raise DoesNotExist("this user does not have an app yet")
        app.name = body.name
        await app.save()

    async def get_info(self, app_id: str) -> AppInfoResponse:
        app = await App.get(id=app_id).prefetch_related("audits")

        audits = app.audits

        n_audits = len(audits)
        n_contracts = len(set(map(lambda x: x.contract_id, audits)))

        response = AppInfoResponse(
            id=app.id,
            created_at=app.created_at,
            name=app.name,
            n_contracts=n_contracts,
            n_audits=n_audits,
        )

        return response

    async def get_stats(self) -> AllStatsResponse:
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
        findings = {
            audit_type: {level: 0 for level in FindingLevelEnum}
            for audit_type in AuditTypeEnum
        }
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
                findings[finding.audit_type][finding.level] += 1

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
            findings=findings,
            users_timeseries=users_timeseries,
            audits_timeseries=audits_timeseries,
        )

        return response
