import os
from typing import Union

from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from app.utils.types.llm import OutputStructure

llm_client = AsyncOpenAI(
    organization=os.getenv("OPENAI_ORG_ID"),
    project=os.getenv("OPENAI_PROJECT_ID"),
    api_key=os.getenv("OPENAI_API_KEY"),
)

model = OpenAIModel("gpt-4o-mini", provider=OpenAIProvider(openai_client=llm_client))

model_settings = ModelSettings(
    max_tokens=3_000,
    temperature=0.2,
)

agent: Agent[Union[str, OutputStructure]] = Agent(model, model_settings=model_settings)


@agent.system_prompt
def inject_prompt(ctx: RunContext[str]) -> str:
    return ctx.deps


chat_model_settings = ModelSettings(
    max_tokens=500,
    temperature=0.2,
)

chat_agent = Agent(
    model,
    model_settings=chat_model_settings,
    system_prompt=(
        "You are a smart contract auditor, who produced a series of findings for a provided smart contract."
        "Be confident in your original findings, but also be understanding and responsive to the user's requests."
    ),
)
