# noqa: E501

import asyncio
import functools
import os
import threading
from datetime import datetime
from typing import Optional, Tuple

import logfire
from game_sdk.game.custom_types import (
    Argument,
    Function,
    FunctionResult,
    FunctionResultStatus,
)
from game_sdk.game.worker import Worker
from tortoise import Tortoise

from app.api.contract.service import ContractService
from app.config import TORTOISE_ORM
from app.db.models import Audit, Finding
from app.utils.types.enums import AuditStatusEnum, AuditTypeEnum
from app.utils.types.models import FindingSchema
from app.worker.pipelines.audit_generation import LlmPipeline

game_api_key = os.environ.get("GAME_API_KEY")


def run_async_sync(func):
    """
    Decorator to run an async function synchronously in a separate thread
    with its own event loop, handling DB connections properly.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result_container = {}

        def run_async_in_thread():
            async def setup_and_run():
                # Initialize DB connections for this event loop
                await Tortoise.init(config=TORTOISE_ORM)
                try:
                    return await func(*args, **kwargs)
                finally:
                    # Clean up DB connections
                    await Tortoise.close_connections()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logfire.debug(f"Running {func.__name__} in new thread/event loop")
            try:
                res = loop.run_until_complete(setup_and_run())
                result_container["result"] = res
            except Exception as e:
                result_container["exception"] = e
                logfire.exception(f"Exception in async thread for {func.__name__}")
            finally:
                logfire.debug(f"Closing event loop for {func.__name__} in thread")
                loop.close()

        thread = threading.Thread(
            target=run_async_in_thread, name=f"run_async_sync_{func.__name__}"
        )
        thread.start()
        thread.join()

        if "exception" in result_container:
            raise result_container["exception"]
        return result_container.get("result")

    return wrapper


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


@run_async_sync
async def get_contract_code(
    address: str, **kwargs
) -> Tuple[FunctionResultStatus, str, dict]:
    contract_service = ContractService()

    try:
        result = await contract_service.fetch_from_source(address=address)
        logfire.info("result found")

        return (
            FunctionResultStatus.DONE,
            (
                "Successfully fetched smart contract source code."
                "Object can be used to initiate an audit"
            ),
            {"contract": result.model_dump()},
        )
    except Exception as err:
        logfire.exception(str(err))
        return (
            FunctionResultStatus.FAILED,
            "Unable to fetch smart contract source code",
            {},
        )


# @run_async_sync
# async def initiate_audit(
#     contract_id: str,
#     **kwargs,
# ):
#     audit_service = AuditService()

#     auth_state = AuthState(
#         app_id="c6b2eb6b-1ad5-497e-ab96-bdc8de3830f3",
#         consumes_credits=False,
#         role=RoleEnum.APP,
#     )

#     data = EvalBody(contract_id=contract_id, audit_type=AuditTypeEnum.SECURITY)

#     audit = await audit_service.initiate_audit(auth=auth_state, data=data)

#     return (
#         FunctionResultStatus.DONE,
#         "Successfully initiated audit. The results will have to be polled for completion.",
#         {"audit_id": str(audit.id)},
#     )


# @run_async_sync
# async def wait_for_audit_completion(
#     audit_id: str,
#     **kwargs,
# ):
#     audit = await Audit.get(id=audit_id)

#     if audit.status == AuditStatusEnum.WAITING:
#         await asyncio.sleep(2)
#         return (
#             FunctionResultStatus.DONE,
#             "Audit is waiting to be processed",
#             {"audit_status": audit.status},
#         )
#     if audit.status == AuditStatusEnum.PROCESSING:
#         await asyncio.sleep(2)
#         return (
#             FunctionResultStatus.DONE,
#             "Audit is being still being processed.",
#             {"audit_status": audit.status},
#         )

#     return (
#         FunctionResultStatus.DONE,
#         "Audit is complete, and its results can be fetched.",
#         {"audit_status": audit.status},
#     )


# @run_async_sync
# async def get_audit_results(audit_id: str, **kwargs):
#     findings = await Finding.filter(audit_id=audit_id).all()
#     findings = list(map(FindingSchema.model_validate, findings))
#     findings_json = list(map(lambda x: x.model_dump(), findings))

#     return (
#         FunctionResultStatus.DONE,
#         "successfully generated smart contract audit",
#         {"audit_findings": findings_json},
#     )


@run_async_sync
async def generate_audit(
    contract_id: str, **kwargs
) -> Tuple[FunctionResultStatus, str, dict]:
    audit_created = await Audit.create(
        # NOTE: depending on how this is called we can make a FIXED user, or actually pass
        # a user through.
        contract_id=contract_id,
        audit_type=AuditTypeEnum.SECURITY,
        status=AuditStatusEnum.PROCESSING,
    )

    audit = await Audit.get(id=audit_created.id).select_related("contract")

    now = datetime.now()
    pipeline = LlmPipeline(
        audit=audit,
        should_publish=False,
    )

    try:
        await pipeline.generate_candidates()
        result = await pipeline.generate_report()
        await pipeline.write_results(
            response=result,
            status=AuditStatusEnum.SUCCESS,
            processing_time_seconds=(datetime.now() - now).seconds,
        )

    except Exception as err:
        logfire.exception(str(err))
        await pipeline.write_results(
            response=None,
            status=AuditStatusEnum.FAILED,
            processing_time_seconds=(datetime.now() - now).seconds,
        )
    finally:
        audit.processing_time_seconds = (datetime.now() - now).seconds
        await audit.save()

    if audit.status == AuditStatusEnum.SUCCESS:
        findings = await Finding.filter(audit_id=audit.id).all()
        findings = list(map(FindingSchema.model_validate, findings))
        findings_json = list(map(lambda x: x.model_dump(), findings))

        return (
            FunctionResultStatus.DONE,
            "successfully generated smart contract audit",
            {"audit_findings": findings_json},
        )

    return FunctionResultStatus.FAILED, "failed to generate smart contract audit", {}


# Action space with all executables
action_space = [
    Function(
        fn_name=get_contract_code.__name__,
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
        fn_name=generate_audit.__name__,
        fn_description="Generate smart contract audit",
        args=[
            Argument(
                name="contract_id",
                type="str",
                description="data model reference id for smart contract",
            ),
        ],
        executable=generate_audit,
    ),
    # Function(
    #     fn_name=initiate_audit.__name__,
    #     fn_description="Initiate the smart contract audit",
    #     args=[
    #         Argument(
    #             name="contract_id",
    #             type="str",
    #             description="data model reference id for smart contract",
    #         )
    #     ],
    #     executable=initiate_audit,
    # ),
    # Function(
    #     fn_name=wait_for_audit_completion.__name__,
    #     fn_description="Poll the status of the audit. To be called until audit_status resolves to success or failed.",
    #     args=[
    #         Argument(
    #             name="audit_id",
    #             type="str",
    #             description="data model reference id for the audit",
    #         )
    #     ],
    #     executable=wait_for_audit_completion,
    # ),
    # Function(
    #     fn_name=get_audit_results.__name__,
    #     fn_description="Get the audit findings. Only to be called once the audit is ready.",
    #     args=[
    #         Argument(
    #             name="audit_id",
    #             type="str",
    #             description="data model reference id for the audit",
    #         )
    #     ],
    #     executable=get_audit_results,
    # ),
]


worker = Worker(
    api_key=game_api_key,
    description="You are a smart contract auditor",
    instruction=(
        "Given the smart contract address, extract the code and generate an audit"
    ),
    get_state_fn=get_state_fn,
    action_space=action_space,
    model_name="Llama-3.3-70B-Instruct",
)
