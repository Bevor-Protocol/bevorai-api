from typing import List, Optional

from pydantic import BaseModel, Field

from app.utils.enums import AuditStatusEnum, AuditTypeEnum, NetworkEnum


class FilterParams(BaseModel):
    user_id: Optional[str]
    page: int
    page_size: int
    search: Optional[str]
    audit_type: List[AuditTypeEnum] = Field(default_factory=list)
    results_status: Optional[AuditStatusEnum]
    network: List[NetworkEnum] = Field(default_factory=list)
    contract_address: Optional[str]
