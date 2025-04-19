from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from app.db.models import Contract
from app.lib.clients.llm import llm_client
from app.utils.types.common import ModelId
from app.utils.types.enums import ContractMethodEnum

model = OpenAIModel("gpt-4o-mini", provider=OpenAIProvider(openai_client=llm_client))

chat_model_settings = ModelSettings(
    max_tokens=500,
    temperature=0.2,
)


@dataclass
class ChatDeps:
    user_id: ModelId
    audit_id: ModelId
    contract_id: ModelId


chat_agent = Agent(
    model,
    model_settings=chat_model_settings,
    system_prompt=(
        "You are a smart contract auditor, who produced a series of findings for a provided smart contract."
        "Be confident in your original findings, but also be understanding and responsive to the user's requests."
        "You are to be terse in your responses. Straightforward and to the point."
    ),
    deps_type=ChatDeps,
)


@chat_agent.tool
async def get_contract_metadata(ctx: RunContext[ChatDeps]):
    contract = await Contract.get(id=ctx.deps.contract_id)

    string = f"Retrieval Method: {contract.method.value}\n"
    if contract.method == ContractMethodEnum.SCAN:
        string += f"Address: {contract.address}\n"
        string += f"Network: {contract.network}\n"
        string += f"Is Proxy: {contract.is_proxy}"
    else:
        string += (
            "Since the contract was uploaded, there's no additional metadata available"
        )

    return string
