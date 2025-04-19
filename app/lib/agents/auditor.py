from typing import Union

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from app.lib.clients.llm import llm_client
from app.utils.types.llm import OutputStructure

model = OpenAIModel("gpt-4o-mini", provider=OpenAIProvider(openai_client=llm_client))

model_settings = ModelSettings(
    max_tokens=3_000,
    temperature=0.2,
)

agent: Agent[Union[str, OutputStructure]] = Agent(model, model_settings=model_settings)


@agent.system_prompt
def inject_prompt(ctx: RunContext[str]) -> str:
    return ctx.deps
