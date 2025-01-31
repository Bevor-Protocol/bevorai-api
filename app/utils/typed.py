from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer

from app.utils.enums import AuditStatusEnum, AuditTypeEnum, NetworkEnum


class FilterParams(BaseModel):
    user_id: Optional[Union[str, UUID]] = Field(default=None)
    page: int
    page_size: int
    search: Optional[str] = Field(default=None)
    audit_type: List[AuditTypeEnum] = Field(default_factory=list)
    status: Optional[AuditStatusEnum] = Field(default=None)
    network: List[NetworkEnum] = Field(default_factory=list)
    contract_address: Optional[str] = Field(default=None)

    @field_serializer("user_id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id
