from pydantic import BaseModel, Field

from app.utils.enums import AuditTypeEnum


class EvalBody(BaseModel):
    contract: str
    audit_type: AuditTypeEnum = Field(default=AuditTypeEnum.GAS)
    encode_code: bool = Field(default=False)
    as_markdown: bool = Field(default=False)
