# app/utils/types/common.py
from typing import TypeAlias, Union
from uuid import UUID

ModelId: TypeAlias = Union[str, UUID]
NullableModelId: TypeAlias = Union[ModelId, None]
