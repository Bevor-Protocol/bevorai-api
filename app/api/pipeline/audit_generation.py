import asyncio
import json
import re
from datetime import datetime

from openai.types.chat import ChatCompletionMessageParam, ParsedChoice
from utils.logger import get_logger

from app.api.pricing.service import Usage
from app.config import redis_client
from app.db.models import Audit, Finding, IntermediateResponse, Prompt
from app.lib.clients import llm_client
from app.utils.schema.output import GasOutputStructure, SecurityOutputStructure
from app.utils.types.enums import AuditStatusEnum, AuditTypeEnum, FindingLevelEnum

logger = get_logger("worker")


class LlmPipeline:

    def __init__(
        self,
        audit: Audit,
        input: str,
        should_publish: bool = False,  # **to pubsub channel**
    ):
        self.input = input

        self.audit = audit
        self.audit_type = audit.audit_type
        self.usage = Usage()

        self.output_structure = (
            GasOutputStructure
            if audit.audit_type == AuditTypeEnum.GAS
            else SecurityOutputStructure
        )

        self.should_publish = should_publish

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

        message = {
            "type": "eval",
            "name": name,
            "status": status,
            "job_id": str(self.audit.id),
        }

        await redis_client.publish(
            "evals",
            json.dumps(message),
        )

    async def __checkpoint(
        self,
        step: str,
        status: AuditStatusEnum,
        result: str | None = None,
        processing_time: int | None = None,
    ):

        checkpoint = await IntermediateResponse.filter(
            audit_id=self.audit.id, step=step
        ).first()

        if checkpoint:
            checkpoint.status = status
            checkpoint.result = result
            checkpoint.processing_time_seconds = processing_time
            await checkpoint.save()
            return

        await IntermediateResponse.create(
            audit_id=self.audit.id,
            step=step,
            status=status,
            result=result,
            processing_time_seconds=processing_time,
        )

    async def __write_findings(self, response):

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
            logger.warning("Failed to parse json, skipping")
            return

        model = self.output_structure(**parsed)

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
        now = datetime.now()
        try:
            await self.__checkpoint(step=candidate, status=AuditStatusEnum.PROCESSING)
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
            await self.__checkpoint(
                step=candidate,
                status=AuditStatusEnum.SUCCESS,
                result=result,
                processing_time=(datetime.now() - now).seconds,
            )

            return result

        except Exception as err:
            logger.warning(err)
            await self.__publish_event(name=candidate, status="error")
            await self.__checkpoint(
                step=candidate,
                status=AuditStatusEnum.FAILED,
                processing_time=(datetime.now() - now).seconds,
            )
            return None

    async def generate_candidates(self):
        tasks = []
        candidate_prompts = await Prompt.filter(
            audit_type=self.audit_type, is_active=True, tag__not="reviewer"
        )
        for prompt in candidate_prompts:
            task = self._generate_candidate(candidate=prompt.tag, prompt=prompt.content)
            tasks.append(task)

        responses: list[str | None] = await asyncio.gather(*tasks)

        constructed_prompt = ""

        for i, response in enumerate(responses):
            if response is not None:
                constructed_prompt += f"\n\nAuditor #{i + 1} Findings:\n{response}"

        self.candidate_prompt = constructed_prompt

    async def generate_report(self):
        if not self.candidate_prompt:
            raise NotImplementedError("must run generate_candidates() first")

        await self.__publish_event(name="report", status="start")

        prompt = await Prompt.filter(
            audit_type=self.audit_type, is_active=True, tag="reviewer"
        ).first()

        now = datetime.now()
        await self.__checkpoint(step="report", status=AuditStatusEnum.PROCESSING)

        try:
            response = await llm_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                max_completion_tokens=2000,
                temperature=0.2,
                messages=[
                    {
                        "role": "developer",
                        "content": prompt.content,
                    },
                    {"role": "user", "content": self.candidate_prompt},
                ],
                response_format=self.output_structure,
            )
        except Exception as err:
            await self.__publish_event(name="report", status="error")
            await self.__checkpoint(
                step="report",
                status=AuditStatusEnum.FAILED,
                processing_time=(datetime.now() - now).seconds,
            )
            raise err

        result = response.choices[0].message.content

        usage = response.usage
        self.usage.add_input(usage.prompt_tokens)
        self.usage.add_output(usage.completion_tokens)
        await self.__publish_event(name="report", status="done")
        await self.__checkpoint(
            step="report",
            status=AuditStatusEnum.SUCCESS,
            processing_time=(datetime.now() - now).seconds,
        )
        await self.__write_findings(result)

        return result
