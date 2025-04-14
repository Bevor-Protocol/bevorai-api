# noqa: E501

import asyncio
import os
from datetime import datetime
from typing import Optional, Tuple

from game_sdk.game.custom_types import (
    Argument,
    Function,
    FunctionResult,
    FunctionResultStatus,
)
from game_sdk.game.worker import Worker

from app.api.contract.service import ContractService
from app.db.models import Audit, Finding
from app.utils.types.enums import AuditStatusEnum, AuditTypeEnum
from app.utils.types.models import FindingSchema
from app.worker.pipelines.audit_generation import LlmPipeline

game_api_key = os.environ.get("GAME_API_KEY")


def get_state_fn(
    function_result: FunctionResult, current_state: Optional[dict] = None
) -> dict:
    info = function_result.info

    initial_state = {}

    if current_state is None:
        # at the first step, initialise the state with just the init state
        return initial_state
    if not info:
        return current_state

    current_state.update(info)

    return current_state


def get_contract_code(address: str, **kwargs) -> Tuple[FunctionResultStatus, str, dict]:
    contract_service = ContractService()

    try:
        result = asyncio.run(contract_service.fetch_from_source(address=address))

        return (
            FunctionResultStatus.DONE,
            (
                "Successfully fetched smart contract source code."
                "Object can be used to initiate an audit"
            ),
            {"contract": result.model_dump()},
        )
    except Exception:
        return (
            FunctionResultStatus.FAILED,
            "Unable to fetch smart contract source code",
            {},
        )


def generate_audit(
    contract_id: str, audit_type: AuditTypeEnum, **kwargs
) -> Tuple[FunctionResultStatus, str, dict]:
    audit = asyncio.run(
        Audit.create(
            contract_id=contract_id,
            audit_type=audit_type,
            status=AuditStatusEnum.PROCESSING,
        )
    )

    now = datetime.now()
    pipeline = LlmPipeline(
        input=audit.contract.code,
        audit=audit,
        should_publish=False,
    )

    try:
        asyncio.run(pipeline.generate_candidates())
        asyncio.run(pipeline.generate_report())
        audit.status = AuditStatusEnum.SUCCESS
    except Exception:
        audit.status = AuditStatusEnum.FAILED
    finally:
        audit.processing_time_seconds = (datetime.now() - now).seconds
        asyncio.run(audit.save())

    if audit.status == AuditStatusEnum.SUCCESS:
        findings = asyncio.run(Finding.filter(audit_id=audit.id).all())
        findings = list(map(FindingSchema.model_validate, findings))

        return (
            FunctionResultStatus.DONE,
            "successfully generated smart contract audit",
            {"audit_findings": findings},
        )

    return FunctionResultStatus.FAILED, "failed to generate smart contract audit", {}


# Action space with all executables
action_space = [
    Function(
        fn_name="get_contract_code",
        fn_description="Extract smart contract code",
        args=[
            Argument(
                name="address",
                type="str",
                description="contract address to receive source code for",
            )
        ],
        executable=get_contract_code,
    ),
    Function(
        fn_name="generate_audit",
        fn_description="Generate smart contract audit",
        args=[
            Argument(
                name="contract_id",
                type="str",
                description="data model reference id for smart contract",
            ),
            Argument(
                name="audit_type",
                type="enum",
                description="type of audit to generate (AuditTypeEnum)",
            ),
        ],
        executable=generate_audit,
    ),
]


worker = Worker(
    api_key=game_api_key,
    description="You are a smart contract auditor",
    instruction=(
        "Given the smart contract address, extract the code and generate an audit"
    ),
    get_state_fn=get_state_fn,
    action_space=action_space,
    model_name="Llama-3.1-405B-Instruct",
)
