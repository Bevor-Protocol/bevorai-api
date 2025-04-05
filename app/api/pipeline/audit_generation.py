import asyncio
import json
import re
from datetime import datetime

from openai.types.chat import ChatCompletionMessageParam, ParsedChoice

from app.api.pricing.service import Usage
from app.config import redis_client
from app.db.models import Audit, Finding, IntermediateResponse, Prompt
from app.lib.clients import llm_client
from app.utils.logger import get_logger
from app.utils.types.enums import AuditStatusEnum, AuditTypeEnum, FindingLevelEnum

from .types import GasOutputStructure, SecurityOutputStructure

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

    async def _publish_event(self, name: str, status: str):
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

    async def _checkpoint(
        self,
        prompt: Prompt,
        status: AuditStatusEnum,
        result: str | None = None,
        processing_time: int | None = None,
    ):
        checkpoint = await IntermediateResponse.filter(
            audit_id=self.audit.id, prompt_id=prompt.id
        ).first()

        logger.info(
            "Checkpointing audit intermediate response",
            extra={
                "audit_id": str(self.audit.id),
                "status": status,
                "step": prompt.tag,
                "processing_time_seconds": processing_time,
            },
        )

        if checkpoint:
            checkpoint.status = status
            checkpoint.result = result
            checkpoint.processing_time_seconds = processing_time
            await checkpoint.save()
            return

        await IntermediateResponse.create(
            audit_id=self.audit.id,
            prompt=prompt,
            step=prompt.tag,
            status=status,
            result=result,
            processing_time_seconds=processing_time,
        )

    async def _write_findings(self, response):
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
            logger.warning(
                "unable to parse json for audit findings, skipping",
                extra={"audit_id": str(self.audit.id)},
            )
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

    async def _generate_candidate(self, prompt: Prompt):
        await self._publish_event(name=prompt.tag, status="start")

        # allows for some fault tolerance.
        now = datetime.now()
        try:
            await self._checkpoint(prompt=prompt, status=AuditStatusEnum.PROCESSING)
            response = await llm_client.chat.completions.create(
                model="gpt-4o-mini",
                max_completion_tokens=2000,
                temperature=0.3,
                messages=[
                    {
                        "role": "developer",
                        "content": prompt.content,
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
            await self._publish_event(name=prompt.tag, status="done")
            await self._checkpoint(
                prompt=prompt,
                status=AuditStatusEnum.SUCCESS,
                result=result,
                processing_time=(datetime.now() - now).seconds,
            )

            return result

        except Exception as err:
            logger.warning(err)
            await self._publish_event(name=prompt.tag, status="error")
            await self._checkpoint(
                prompt=prompt,
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
            task = self._generate_candidate(prompt)
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

        prompt = await Prompt.filter(
            audit_type=self.audit_type, is_active=True, tag="reviewer"
        ).first()

        await self._publish_event(name=prompt.tag, status="start")

        now = datetime.now()
        await self._checkpoint(prompt=prompt, status=AuditStatusEnum.PROCESSING)

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
            await self._publish_event(name=prompt.tag, status="error")
            await self._checkpoint(
                prompt=prompt,
                status=AuditStatusEnum.FAILED,
                processing_time=(datetime.now() - now).seconds,
            )
            raise err

        result = response.choices[0].message.content

        usage = response.usage
        self.usage.add_input(usage.prompt_tokens)
        self.usage.add_output(usage.completion_tokens)
        await self._publish_event(name=prompt.tag, status="done")
        await self._checkpoint(
            prompt=prompt,
            status=AuditStatusEnum.SUCCESS,
            result=result,
            processing_time=(datetime.now() - now).seconds,
        )
        await self._write_findings(result)

        return result

        return result
        return result
