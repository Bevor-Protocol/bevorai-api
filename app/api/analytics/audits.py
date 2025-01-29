import base64
import logging
import math
from collections import defaultdict

import anyio

from app.api.ai.eval import EvalService
from app.api.depends.auth import UserDict
from app.db.models import App, Audit, Auth, Contract, User
from app.pydantic.response import (
    AnalyticsAudit,
    AnalyticsContract,
    AnalyticsResponse,
    StatsResponse,
)
from app.utils.enums import AuditTypeEnum
from app.utils.typed import FilterParams


def encode_cursor(cursor: str) -> str:
    return base64.urlsafe_b64encode(cursor.encode()).decode()


def decode_cursor(cursor: str) -> str:
    return base64.urlsafe_b64decode(cursor.encode()).decode()


async def get_audits(user: UserDict, query: FilterParams) -> AnalyticsResponse:

    limit = query.page_size
    offset = query.page * limit

    filter = {}

    if query.search:
        filter["results_raw_output__icontains"] = query.search
    if query.audit_type:
        filter["audit_type__in"] = query.audit_type
    if query.network:
        filter["contract__network__in"] = query.network
    if query.contract_address:
        filter["contract__address__icontains"] = query.contract_address
    if query.user_id:
        filter["user__address__icontains"] = query.user_id

    if user["app"]:
        filter["app_id"] = user["app"].id
    else:
        filter["user_id"] = user["user"].id

    await anyio.sleep(2)

    total = await Audit.all().count()

    total_pages = math.ceil(total / query.page_size)

    if total <= offset:
        return AnalyticsResponse(results=[], more=False, total_pages=total_pages)

    results = (
        await Audit.filter(**filter)
        .order_by("created_at")
        .offset(offset)
        .limit(limit + 1)
        .values(
            "id",
            "created_at",
            "app_id",
            "user__address",
            "audit_type",
            "results_status",
            "contract__id",
            "contract__method",
            "contract__address",
            "contract__network",
        )
    )

    data = []
    for i, result in enumerate(results[:-1]):
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
            app_id=str(result["app_id"]),
            user_id=result["user__address"],
            audit_type=result["audit_type"],
            results_status=result["results_status"],
            contract=contract,
        )
        data.append(response)

    return AnalyticsResponse(
        results=data, more=len(results) > query.page_size, total_pages=total_pages
    )


async def get_stats():
    await anyio.sleep(3)
    n_audits = 0
    n_contracts = await Contract.all().count()
    n_users = await User.all().count()
    n_apps = await App.all().count()
    n_auths = await Auth.all().count()

    gas_findings = defaultdict(int)
    security_findings = defaultdict(int)

    for audit in await Audit.all():
        n_audits += 1
        try:
            parsed = EvalService.sanitize_data(
                raw_data=audit.results_raw_output,
                audit_type=audit.audit_type,
                as_markdown=False,
            )
        except Exception as err:
            logging.warn(f"could not parse {audit.id}")
            logging.warn(err)
            continue
        for k, v in parsed["findings"].items():
            if audit.audit_type == AuditTypeEnum.SECURITY:
                security_findings[k] += len(v)
            else:
                gas_findings[k] += len(v)

    response = StatsResponse(
        n_apps=n_apps,
        n_auths=n_auths,
        n_users=n_users,
        n_contracts=n_contracts,
        n_audits=n_audits,
        findings={
            AuditTypeEnum.GAS: gas_findings,
            AuditTypeEnum.SECURITY: security_findings,
        },
    )

    return response


async def get_audit(id: str) -> str:
    audit = await Audit.get(id=id).select_related("contract", "user")

    result = EvalService.sanitize_data(
        raw_data=audit.results_raw_output,
        audit_type=audit.audit_type,
        as_markdown=True,
    )

    return {
        "contract": {
            "address": audit.contract.address,
            "network": audit.contract.network,
            "code": audit.contract.raw_code,
        },
        "user": {
            "id": str(audit.user.id),
            "address": audit.user.address,
        },
        "audit": {
            "model": audit.model,
            "prompt_version": audit.prompt_version,
            "audit_type": audit.audit_type,
            "result": result,
        },
    }
