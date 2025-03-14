# flake8: noqa

from typing import Any

from pydantic import BaseModel
from typing_extensions import NotRequired, TypedDict


class OpenApiParams(TypedDict, total=False):
    summary: NotRequired[str]
    description: NotRequired[str]
    response_model: NotRequired[type[BaseModel]]
    response_description: NotRequired[str] = "Successful Response"
    deprecated: NotRequired[bool]
    include_in_schema: NotRequired[bool]
    responses: NotRequired[dict[int | str, dict[str, Any]]]
