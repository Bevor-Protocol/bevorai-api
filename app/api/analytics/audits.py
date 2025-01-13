import logging
from collections import defaultdict

import anyio

from app.api.ai.eval import sanitize_data
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


async def get_audits(user: UserDict, query: FilterParams):

    page_size = query.pop("page_size")
    page = query.pop("page")
    search = query.pop("search")

    limit = page_size
    offset = (page) * page_size

    filter = {}
    for k, v in query.items():
        if v:
            filter[k] = v

    if search:
        filter["results_raw_output__icontains"] = search

    if user["app"]:
        filter["app_id"] = user["app"].id
    else:
        filter["user_id"] = user["user"].id

    await anyio.sleep(5)

    results = (
        await Audit.filter(**filter)
        .order_by("created_at")
        .offset(offset)
        .values(
            "id",
            "app_id",
            "user__address",
            "audit_type",
            "results_status",
            "contract__method",
            "contract__address",
            "contract__network",
        )
    )[: (limit + 1)]

    data = []
    for result in results[:-1]:
        contract = AnalyticsContract(
            method=result["contract__method"],
            address=result["contract__address"],
            network=result["contract__network"],
        )
        response = AnalyticsAudit(
            id=str(result["id"]),
            app_id=str(result["app_id"]),
            user_id=result["user__address"],
            audit_type=result["audit_type"],
            results_status=result["results_status"],
            contract=contract,
        )
        data.append(response)

    return AnalyticsResponse(results=data, more=len(results) > page_size)


async def get_stats():
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
            parsed = sanitize_data(
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
