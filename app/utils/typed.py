from typing import Optional, TypedDict

from app.utils.enums import AuditStatusEnum, AuditTypeEnum


class FilterParams(TypedDict):
    user_id: Optional[str]
    page: int
    page_size: int
    search: Optional[str]
    audit_type: Optional[AuditTypeEnum]
    results_status: Optional[AuditStatusEnum]
