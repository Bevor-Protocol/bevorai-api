from typing import TypedDict

from pydantic import BaseModel


class Candidates(TypedDict):
    candidates: dict[str, str]
    reviewer: str


class VersionDict(TypedDict):
    markdown: str
    prompts: Candidates
    response: BaseModel
