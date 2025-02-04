from typing import Optional
from xmlrpc.client import boolean

from pydantic import BaseModel, Field

from app.utils.enums import AuditTypeEnum, ModelTypeEnum, NetworkEnum


class EvalBody(BaseModel):
    contract_id: str
    audit_type: AuditTypeEnum = Field(default=AuditTypeEnum.GAS)
    model_type: Optional[ModelTypeEnum] = Field(default=ModelTypeEnum.LLAMA3)
    webhook_url: Optional[str] = Field(default=None)


class EvalAgentBody(BaseModel):
    contract_id: str
    audit_type: AuditTypeEnum = Field(default=AuditTypeEnum.GAS)
    model_type: Optional[ModelTypeEnum] = Field(default=ModelTypeEnum.LLAMA3)
    webhook_url: Optional[str] = Field(default=None)
    twitter_handle: Optional[str] = Field(
        default=None, description="Twitter handle for the agent"
    )
    cookiedao_link: Optional[str] = Field(
        default=None, description="Link to agent's CookieDAO profile"
    )


class ContractUploadBody(BaseModel):
    code: str
    network: Optional[NetworkEnum] = Field(default=None)


class FeedbackBody(BaseModel):
    id: str
    feedback: Optional[str] = Field(default=None)
    verified: boolean
