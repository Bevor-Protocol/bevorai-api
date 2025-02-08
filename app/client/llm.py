import os

from openai import AsyncOpenAI

llm_client = AsyncOpenAI(
    organization=os.getenv("OPENAI_ORG_ID"),
    project=os.getenv("OPENAI_PROJECT_ID"),
    api_key=os.getenv("OPENAI_API_KEY"),
)
