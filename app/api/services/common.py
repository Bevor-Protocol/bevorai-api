import asyncio
import json
import logging
import re

from openai.types.chat import ChatCompletionMessageParam, ParsedChoice

from app.client.llm import llm_client
from app.config import redis_client
from app.db.models import Audit, Finding, IntermediateResponse
from app.lib.gas import CURRENT_VERSION as gas_version
from app.lib.gas import structure as gas_structure
from app.lib.security import CURRENT_VERSION as sec_version
from app.lib.security import structure as sec_structure
from app.utils.enums import AuditTypeEnum, FindingLevelEnum
from app.utils.pricing import Usage


class LlmPipeline:

    def __init__(
        self,
        audit: Audit,
        input: str,
        should_publish: bool = False,  # **to pubsub channel**
        should_write_to_db: bool = False,  # **for intermediate response**
    ):
        self.input = input

        self.audit = audit
        self.audit_type = audit.audit_type
        self.usage = Usage()

        # will always use the most recent version
        self.version_use = (
            sec_structure
            if audit.audit_type == AuditTypeEnum.SECURITY
            else gas_structure
        )
        self.version = (
            sec_version if audit.audit_type == AuditTypeEnum.SECURITY else gas_version
        )
        self.should_publish = should_publish
        self.should_write_to_db = should_write_to_db

    def _parse_candidates(
        self, choices: list[ParsedChoice]
    ) -> ChatCompletionMessageParam:
        constructed_prompt = ""

        for choice in choices:
            constructed_prompt += f"\n\n{choice.message.content}"

        return {"role": "assistant", "content": choice.message.content}

    async def __publish_event(self, name: str, status: str):
        if not self.should_publish:
            return

        await redis_client.publish(
            "evals",
            json.dumps(
                {
                    "type": "eval",
                    "name": name,
                    "status": status,
                    "job_id": str(self.audit.id),
                }
            ),
        )

    async def __write_checkpoint(self, step: str, result: str | list[str]):
        if not self.should_write_to_db:
            return

        await IntermediateResponse.create(
            audit_id=self.audit.id,
            step=step,
            result=result,
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

        output_parser = self.version_use["response"]

        model = output_parser(**parsed)

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

    async def _generate_candidate(self, candidate: str, prompt: str):
        await self.__publish_event(name=candidate, status="start")

        # allows for some fault tolerance.
        try:
            response = await llm_client.chat.completions.create(
                model="gpt-4o-mini",
                max_completion_tokens=2000,
                temperature=0.3,
                messages=[
                    {
                        "role": "developer",
                        "content": prompt,
                    },
                    {
                        "role": "user",
                        "content": self.input,
                    },
                ],
            )
            usage = response.usage
            self.usage.add_input(usage.prompt_tokens)
            self.usage.add_output(usage.completion_tokens)
            result = response.choices[0].message.content
            await self.__publish_event(name=candidate, status="done")
            await self.__write_checkpoint(step=candidate, result=result)

            return result

        except Exception as err:
            logging.warning(err)
            await self.__publish_event(name=candidate, status="error")
            return None

    async def generate_candidates(self):
        tasks = []
        candidate_prompts = self.version_use["prompts"]["candidates"]
        for candidate, prompt in candidate_prompts.items():
            task = self._generate_candidate(candidate=candidate, prompt=prompt)
            tasks.append(task)

        responses: list[str | None] = await asyncio.gather(*tasks)

        constructed_prompt = ""

        for i, response in enumerate(responses):
            if response is not None:
                constructed_prompt += f"\n\nAuditor #{i + 1} Findings:\n{response}"

        self.candidate_prompt = constructed_prompt

    async def generate_report(self):
        if not self.candidate_prompt:
            raise NotImplementedError("must run generate_judgement() first")

        await self.__publish_event(name="report", status="start")

        output_structure = self.version_use["response"]
        prompt = self.version_use["prompts"]["reviewer"]

        try:
            response = await llm_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                max_completion_tokens=2000,
                temperature=0.2,
                messages=[
                    {
                        "role": "developer",
                        "content": prompt,
                    },
                    {"role": "user", "content": self.candidate_prompt},
                ],
                response_format=output_structure,
            )
        except Exception as err:
            await self.__publish_event(name="report", status="error")
            raise err

        result = response.choices[0].message.content

        usage = response.usage
        self.usage.add_input(usage.prompt_tokens)
        self.usage.add_output(usage.completion_tokens)
        await self.__publish_event(name="report", status="done")
        await self.__write_findings(result)

        return result
