import json
import logging
import os
import re
from typing import List, Optional, Union

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ParsedChoice

from app.cache import redis_client
from app.db.models import Audit, Finding, IntermediateResponse
from app.lib.v1.prompts import formatters, prompts
from app.utils.enums import FindingLevelEnum, IntermediateResponseEnum

client = AsyncOpenAI(
    organization=os.getenv("OPENAI_ORG_ID"),
    project=os.getenv("OPENAI_PROJECT_ID"),
    api_key=os.getenv("OPENAI_API_KEY"),
)


class LlmPipeline:

    def __init__(
        self,
        audit: Audit,
        input: str,
        model: Optional[str] = None,
        should_publish: bool = False,  # **to pubsub channel**
        should_write_to_db: bool = False,  # **for intermediate response**
    ):
        self.input = input
        self.model = model or "gpt-4o-mini"

        self.audit = audit
        self.audit_type = audit.audit_type
        self.base_prompts = prompts[audit.audit_type]
        self.formatter = formatters[audit.audit_type]
        self.should_publish = should_publish
        self.should_write_to_db = should_write_to_db

    def _parse_candidates(
        self, choices: List[ParsedChoice]
    ) -> ChatCompletionMessageParam:
        constructed_prompt = ""

        for choice in choices:
            constructed_prompt += f"\n\n{choice.message.content}"

        return {"role": "assistant", "content": choice.message.content}

    async def __publish_event(self, step: str):
        if not self.should_publish:
            return

        await redis_client.publish(
            "evals",
            json.dumps(
                {
                    "type": "eval",
                    "step": step,
                    "job_id": str(self.audit.id),
                }
            ),
        )

    async def __write_checkpoint(
        self, step: IntermediateResponseEnum, result: Union[str, List[str]]
    ):
        if not self.should_write_to_db:
            return
        if isinstance(result, list):
            await IntermediateResponse.bulk_create(
                objects=list(
                    map(
                        lambda content: IntermediateResponse(
                            audit_id=self.audit.id,
                            step=step,
                            result=content,
                        ),
                        result,
                    )
                )
            )
        else:
            await IntermediateResponse.create(
                audit_id=self.audit.id, step=step, result=result
            )

    async def __write_findings(self, response):
        if not self.should_write_to_db:
            return

        pattern = r"<<(.*?)>>"

        # this parsing should not be required, but we'll include it for safety
        raw_data = re.sub(pattern, r"`\1`", response)

        # corrects for occassional leading non-json text...
        pattern = r"\{.*\}"
        match = re.search(pattern, raw_data, re.DOTALL)
        if match:
            raw_data = match.group(0)

        try:
            parsed = json.loads(raw_data)
        except Exception:
            logging.warn("Failed to parse json, skipping")
            return

        model = self.formatter(**parsed)

        to_create = []
        for severity in FindingLevelEnum:
            findings = getattr(model.findings, severity.value, None)
            if findings:
                for finding in findings:
                    to_create.append(
                        Finding(
                            audit=self.audit,
                            audit_type=self.audit_type,
                            level=severity,
                            name=finding.name,
                            explanation=finding.explanation,
                            recommendation=finding.recommendation,
                            reference=finding.reference,
                        )
                    )

        if to_create:
            await Finding.bulk_create(objects=to_create)

    async def generate_candidates(self, n: int = 3):
        await self.__publish_event(step="generating_candidates")

        try:
            response = await client.chat.completions.create(
                model=self.model,
                max_completion_tokens=2000,
                n=max(0, min(n, 4)),
                temperature=0.5,
                messages=[
                    {
                        "role": "developer",
                        "content": self.base_prompts[
                            IntermediateResponseEnum.CANDIDATE
                        ],
                    },
                    {
                        "role": "user",
                        "content": self.input,
                    },
                ],
            )
        except Exception as err:
            await self.__publish_event(step="error")
            raise err

        constructed_prompt = ""

        for i, choice in enumerate(response.choices):
            constructed_prompt += (
                f"\n\nAuditor #{i + 1} Findings:\n{choice.message.content}"
            )

        self.candidate_prompt = constructed_prompt

        contents = list(map(lambda x: x.message.content, response.choices))

        await self.__write_checkpoint(
            step=IntermediateResponseEnum.CANDIDATE, result=contents
        )

    async def generate_judgement(self):
        if not self.candidate_prompt:
            raise NotImplementedError("must run generate_candidates() first")

        await self.__publish_event(step="generating_judgements")

        judgement_user_input = (
            "Here is the original smart contract:\n\n{contract}"
            "\n\nHere are the auditor findings that you are to review:\n\n"
            "{candidate_prompt}"
        )
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                max_completion_tokens=2000,
                temperature=0.2,
                messages=[
                    {
                        "role": "developer",
                        "content": self.base_prompts[IntermediateResponseEnum.REVIEWER],
                    },
                    {
                        "role": "user",
                        "content": judgement_user_input.format(
                            contract=self.input, candidate_prompt=self.candidate_prompt
                        ),
                    },
                ],
            )
        except Exception as err:
            await self.__publish_event(step="error")
            raise err

        self.judgement_prompt = response.choices[0].message.content

        await self.__write_checkpoint(
            step=IntermediateResponseEnum.REVIEWER,
            result=response.choices[0].message.content,
        )

    async def generate_report(self):
        if not self.judgement_prompt:
            raise NotImplementedError("must run generate_judgement() first")

        await self.__publish_event(step="generating_report")

        report_user_input = (
            f"Generate a report based on the following "
            f"critique: {self.judgement_prompt}"
        )
        try:
            response = await client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                max_completion_tokens=2000,
                temperature=0.1,
                messages=[
                    {
                        "role": "developer",
                        "content": self.base_prompts[IntermediateResponseEnum.REPORTER],
                    },
                    {"role": "user", "content": report_user_input},
                ],
                response_format=self.formatter,
            )
        except Exception as err:
            await self.__publish_event(step="error")
            raise err

        result = response.choices[0].message.content

        await self.__publish_event(step="done")
        await self.__write_findings(result)

        return result
