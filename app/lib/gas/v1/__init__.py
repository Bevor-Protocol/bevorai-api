from app.utils.schema.llm import VersionDict

from .markdown import template
from .prompt import prompts
from .response import OutputStructure

structure = VersionDict(markdown=template, prompts=prompts, response=OutputStructure)
