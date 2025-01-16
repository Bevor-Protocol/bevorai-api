import os
from typing import List

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ParsedChoice

from app.lib.v1.prompts.security import (
    OutputStructure,
    candidate_prompt,
    report_prompt,
    reviewer_prompt,
)


class LlmPipeline:

    def __init__(self, input: str):
        self.client = AsyncOpenAI(
            organization=os.getenv("OPENAI_ORG_ID"),
            project=os.getenv("OPENAI_PROJECT_ID"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.input = input

    def _parse_candidates(
        self, choices: List[ParsedChoice]
    ) -> ChatCompletionMessageParam:
        constructed_prompt = ""

        for choice in choices:
            constructed_prompt += f"\n\n{choice.message.content}"

        return {"role": "assistant", "content": choice.message.content}

    async def generate_candidates(self, n: int = 3):
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            max_completion_tokens=1000,
            n=max(0, min(n, 4)),
            temperature=0.5,
            messages=[
                {"role": "developer", "content": candidate_prompt},
                {
                    "role": "user",
                    "content": self.input,
                },
            ],
        )

        constructed_prompt = ""

        for choice in response.choices:
            constructed_prompt += f"\n\n{choice.message.content}"

        self.candidate_prompt = constructed_prompt

    async def generate_judgement(self):
        if not self.candidate_prompt:
            raise NotImplementedError("must run generate_candidates() first")
        judgement_user_input = "Given the original smart contract:\n\n{contract}\n\nReview and critique the following findings:\n\n\{candidate_prompt}"
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            max_completion_tokens=1200,
            temperature=0.2,
            messages=[
                {"role": "developer", "content": reviewer_prompt},
                {
                    "role": "user",
                    "content": judgement_user_input.format(
                        contract=self.input, candidate_prompt=self.candidate_prompt
                    ),
                },
            ],
        )

        self.judgement_prompt = response.choices[0].message.content

    async def generate_report(self):
        if not self.judgement_prompt:
            raise NotImplementedError("must run generate_judgement() first")
        report_user_input = f"Generate a report based on the following critique: {self.judgement_prompt}"
        response = await self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            max_completion_tokens=1200,
            temperature=0.2,
            messages=[
                {"role": "developer", "content": report_prompt},
                {"role": "user", "content": report_user_input},
            ],
            response_format=OutputStructure,
        )

        return response.choices[0].message.content
