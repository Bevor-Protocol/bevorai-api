import datetime
import json
import logging
import os
import re

import httpx
import replicate
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.ai.markdown.gas import markdown as gas_markdown
from app.ai.markdown.security import markdown as security_markdown
from app.ai.prompts.gas import prompt as gas_prompt
from app.ai.prompts.security import prompt as security_prompt
from app.blockchain.services.scan import fetch_contract_source_code_from_explorer
from app.utils.enums import AuditTypeEnum
from app.utils.types import EvalBody

input_template = {
    "min_tokens": 512,
    "max_tokens": 3000,
    "system_prompt": (
        "You are a helpful assistant, specializing in smart contract auditing"
    ),
    "prompt_template": """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    {system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

    {prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """,
}


def parse_branded_markdown(
    audit_type: AuditTypeEnum, findings: dict, encode_code: bool
):
    result = gas_markdown if audit_type == AuditTypeEnum.GAS else security_markdown

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
                if encode_code:
                    finding = re.sub(pattern, r"`\1`", finding)
                finding_str += f"- {finding}\n"

        formatter[key] = finding_str.strip()

    return result.format(**formatter)


async def process_evaluation(data: EvalBody) -> JSONResponse:
    contract_code = data.contract_code
    contract_address = data.contract_address
    network = data.network
    audit_type = data.audit_type
    encode_code = data.encode_code
    as_markdown = data.as_markdown

    if not contract_code:
        async with httpx.AsyncClient() as client:
            response = await fetch_contract_source_code_from_explorer(
                client, network, contract_address
            )
            if not response:
                raise HTTPException(
                    status_code=404,
                    detail="No source code found for the given address on any platform",
                )
            contract = response
    else:
        contract = contract_code

    prompt = gas_prompt if audit_type == AuditTypeEnum.GAS else security_prompt

    if not contract or not prompt:
        raise HTTPException(status_code=400, detail="Must provide input")

    # Insert the code text into the audit prompt
    audit_prompt = prompt.replace("<{prompt}>", contract)
    if encode_code:
        audit_prompt = audit_prompt.replace(
            "<{code_structured}>",
            (
                "If you reference a function or variable directly, wrap it"
                " in place, such that it looks like this <<{code}>>"
                " Do not tack on arbitrary code snippets at the end"
                " of your description.\nie, instead of: "
                "'The use of delegatecall in the _delegate function',"
                " give me: "
                "'The use of delegatecall in the <<_delegate>> function'"
            ),
        )
    else:
        audit_prompt = audit_prompt.replace("<{code_structured}>", "\n")

    input_data = {**input_template, "prompt": audit_prompt}
    try:
        # Initialize Replicate client
        client = replicate.Client(api_token=os.getenv("REPLICATE_API_KEY"))

        # this model returns an iterator
        response = await client.async_run(
            "meta/meta-llama-3-70b-instruct", input=input_data
        )

        response_completed = ""
        for r in response:
            response_completed += r

        parsed = json.loads(response_completed)

        if as_markdown:
            parsed = parse_branded_markdown(
                audit_type=audit_type, findings=parsed, encode_code=encode_code
            )

        return parsed

    except Exception as error:
        logging.fatal(error)
        logging.fatal(error.__traceback__)
        raise HTTPException(status_code=500, detail=str(error))
