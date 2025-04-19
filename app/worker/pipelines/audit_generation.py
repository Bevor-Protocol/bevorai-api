import asyncio
import json
from datetime import datetime
from typing import Any, Coroutine

import logfire

from app.api.pricing.service import CreditCosts
from app.config import redis_client
from app.db.models import Audit, Finding, IntermediateResponse, Prompt
from app.lib.agents.auditor import agent
from app.utils.types.enums import AuditStatusEnum, FindingLevelEnum
from app.utils.types.llm import OutputStructure


class LlmPipeline:
    def __init__(
        self,
        audit: Audit,
        should_publish: bool = False,  # **to pubsub channel**
    ):
        self.audit = audit
        self.audit_type = audit.audit_type
        self.usage = CreditCosts()

        self.should_publish = should_publish
        self.candidate_responses = ""

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

    async def _generate_candidate(self, prompt: Prompt):
        await self._publish_event(name=prompt.tag, status="start")
        await self._checkpoint(prompt=prompt, status=AuditStatusEnum.PROCESSING)

        # allows for some fault tolerance.
        now = datetime.now()
        with logfire.span(
            f"Generating audit candidate {prompt.tag}",
            **{
                "audit_id": str(self.audit.id),
            },
        ):
            try:
                result = await agent.run(self.audit.contract.code, deps=prompt.content)
                runtime = (datetime.now() - now).seconds
                self.candidate_responses += (
                    f"\n\nAuditor #{prompt.tag} Findings:\n{result.data}"
                )

                usage = result.usage()

                self.usage.add_input(usage.request_tokens or 0)
                self.usage.add_output(usage.response_tokens or 0)

                await self._publish_event(name=prompt.tag, status="done")
                await self._checkpoint(
                    prompt=prompt,
                    status=AuditStatusEnum.SUCCESS,
                    result=result.data,
                    processing_time=runtime,
                )

            except Exception as err:
                logfire.warning(str(err))
                runtime = (datetime.now() - now).seconds
                await self._publish_event(name=prompt.tag, status="error")
                await self._checkpoint(
                    prompt=prompt,
                    status=AuditStatusEnum.FAILED,
                    processing_time=runtime,
                )

    async def generate_candidates(self) -> None:
        tasks: list[Coroutine[Any, Any, None]] = []
        candidate_prompts = await Prompt.filter(
            audit_type=self.audit_type, is_active=True, tag__not="reviewer"
        )
        for prompt in candidate_prompts:
            task = self._generate_candidate(prompt)
            tasks.append(task)

        await asyncio.gather(*tasks)

    async def generate_report(self) -> OutputStructure:
        if not self.candidate_responses:
            raise NotImplementedError("must run generate_candidates() first")

        prompt = await Prompt.filter(
            audit_type=self.audit_type, is_active=True, tag="reviewer"
        ).first()

        if not prompt:
            raise Exception("no active reviewer prompt exists")

        await self._publish_event(name=prompt.tag, status="start")
        await self._checkpoint(prompt=prompt, status=AuditStatusEnum.PROCESSING)

        now = datetime.now()

        try:
            result = await agent.run(
                self.candidate_responses.strip(),
                deps=prompt.content,
                result_type=OutputStructure,
            )
            runtime = (datetime.now() - now).seconds

            usage = result.usage()
            self.usage.add_input(usage.request_tokens or 0)
            self.usage.add_output(usage.response_tokens or 0)
        except Exception as err:
            runtime = (datetime.now() - now).seconds
            await self._publish_event(name=prompt.tag, status="error")
            await self._checkpoint(
                prompt=prompt,
                status=AuditStatusEnum.FAILED,
                processing_time=runtime,
            )
            raise err

        await self._publish_event(name=prompt.tag, status="done")
        await self._checkpoint(
            prompt=prompt,
            status=AuditStatusEnum.SUCCESS,
            result=result.data.model_dump_json(),
            processing_time=runtime,
        )

        return result.data

    async def write_results(
        self,
        response: OutputStructure | None,
        status: AuditStatusEnum,
        processing_time_seconds: int,
    ):
        self.audit.status = status
        self.audit.processing_time_seconds = processing_time_seconds

        self.audit.input_tokens = self.usage.input_tokens
        self.audit.output_tokens = self.usage.output_tokens

        if not response:
            await self.audit.save()
            return

        self.audit.raw_output = response.model_dump_json()
        self.audit.introduction = response.introduction
        self.audit.scope = response.scope
        self.audit.conclusion = response.conclusion

        await self.audit.save()

        to_create = []
        finding: Finding
        for severity in FindingLevelEnum:
            findings = getattr(response.findings, severity.value, None)
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
