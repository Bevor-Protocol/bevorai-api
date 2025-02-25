from app.schema.llm import VersionDict

from .markdown import template
from .prompt import prompts
from .response import OutputStructure

structure = VersionDict(response=OutputStructure)
