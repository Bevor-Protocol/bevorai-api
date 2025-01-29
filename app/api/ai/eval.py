import datetime
import json
import logging
import re
from uuid import uuid4

from arq import create_pool
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist

from app.api.blockchain.scan import ContractService
from app.api.middleware.auth import UserDict
from app.db.models import Audit
from app.lib.v1.markdown.gas import markdown as gas_markdown
from app.lib.v1.markdown.security import markdown as security_markdown

# from app.lib.prompts.gas import prompt as gas_prompt
# from app.lib.prompts.security import prompt as security_prompt
from app.pydantic.request import EvalBody
from app.pydantic.response import EvalResponse, EvalResponseData
from app.utils.enums import AuditStatusEnum, AuditTypeEnum, ResponseStructureEnum
from app.worker import WorkerSettings

# from app.worker import process_eval

input_template = {
    "min_tokens": 512,
    "max_tokens": 1500,
    "system_prompt": (
        "You are a helpful assistant, specializing in smart contract auditing"
    ),
    "prompt_template": """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    {system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

    {prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """,
}


class EvalService:

    def __init__(self, audit_type: AuditTypeEnum):
        self.audit_type = audit_type
        self.markdown = (
            gas_markdown if audit_type == AuditTypeEnum.GAS else security_markdown
        )

    @classmethod
    def sanitize_data(self, raw_data: str, as_markdown: bool):
        # sanitizing backslashes/escapes for code blocks
        pattern = r"<<(.*?)>>"
        raw_data = re.sub(pattern, r"`\1`", raw_data)

        # corrects for occassional leading non-json text...
        pattern = r"\{.*\}"
        match = re.search(pattern, raw_data, re.DOTALL)
        if match:
            raw_data = match.group(0)

        parsed = json.loads(raw_data)

        if as_markdown:
            parsed = self.parse_branded_markdown(
                audit_type=self.audit_type, findings=parsed
            )

        return parsed

    def parse_branded_markdown(self, findings: dict):
        result = self.markdown

        formatter = {
            "project_name": findings["audit_summary"].get("project_name", "Unknown"),
            "address": "Unknown",
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "introduction": findings["introduction"],
            "scope": findings["scope"],
            "conclusion": findings["conclusion"],
        }

        pattern = r"<<(.*?)>>"

        rec_string = ""
        for rec in findings["recommendations"]:
            rec_string += f"- {rec}\n"
        formatter["recommendations"] = rec_string.strip()

        for k, v in findings["findings"].items():
            key = f"findings_{k}"
            finding_str = ""
            if not v:
                finding_str = "None Identified"
            else:
                for finding in v:
                    finding = re.sub(pattern, r"`\1`", finding)
                    finding_str += f"- {finding}\n"

            formatter[key] = finding_str.strip()

        return result.format(**formatter)

    async def process_evaluation(self, user: UserDict, data: EvalBody) -> JSONResponse:
        contract_code = data.contract_code
        contract_address = data.contract_address
        contract_network = data.contract_network
        audit_type = data.audit_type
        # webhook_url = data.webhook_url

        contract_service = ContractService()

        contract = await contract_service.fetch_from_source(
            code=contract_code,
            address=contract_address,
            network=contract_network,
        )

        if not contract:
            raise HTTPException(
                status_code=404,
                detail=(
                    "no verified source code found for the contract "
                    "information provided"
                ),
            )

        id = uuid4()

        await Audit.create(
            id=id,
            contract_id=contract["id"],
            app_id=user["app"].id,
            user_id=user["user"].id,
            audit_type=audit_type,
            prompt_version=1,
        )

        worker = await create_pool(WorkerSettings.redis_settings)

        job = await worker.enqueue_job(
            "process_eval",
            audit_id=str(id),
            code=contract_code,
            audit_type=self.audit_type,
        )

        logging.info(job)

        # process_eval.send(
        #     audit_id=str(id), code=contract_code, audit_type=self.audit_type
        # )

        return {"job_id": job.job_id, "id": str(id), "status": AuditStatusEnum.WAITING}

    @classmethod
    async def get_eval(
        self, id: str, response_type: ResponseStructureEnum
    ) -> EvalResponse:
        try:
            audit = await Audit.get(id=id).select_related("contract")
        except DoesNotExist as err:
            logging.error(err)
            response = EvalResponse(
                success=False, exists=False, error="no record of this evaluation exists"
            )
            return response

        response = EvalResponse(
            success=True,
            exists=True,
        )

        data = {
            "id": str(audit.id),
            "response_type": response_type,
            "contract_address": audit.contract.address,
            "contract_code": audit.contract.raw_code,
            "contract_network": audit.contract.network,
            "status": audit.results_status,
        }

        if audit.results_status == AuditStatusEnum.SUCCESS:
            if response_type == ResponseStructureEnum.RAW:
                data["result"] = audit.results_raw_output
            else:
                try:
                    data["result"] = self.sanitize_data(
                        raw_data=audit.results_raw_output,
                        audit_type=audit.audit_type,
                        as_markdown=response_type == ResponseStructureEnum.MARKDOWN,
                    )
                except json.JSONDecodeError as err:
                    logging.error(
                        f"Unable to parse the output correctly for {str(audit.id)}: "
                        f"{err}"
                    )

        response.result = EvalResponseData(**data)

        return response
