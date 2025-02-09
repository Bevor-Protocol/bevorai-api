from typing import Optional
from uuid import UUID
from xmlrpc.client import boolean

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.utils.enums import AuditStatusEnum, AuditTypeEnum, ModelTypeEnum, NetworkEnum


class EvalBody(BaseModel):
    contract_id: str
    audit_type: AuditTypeEnum = Field(default=AuditTypeEnum.GAS)
    model_type: Optional[ModelTypeEnum] = Field(default=ModelTypeEnum.LLAMA3)
    webhook_url: Optional[str] = Field(default=None)


class FeedbackBody(BaseModel):
    id: str
    feedback: Optional[str] = Field(default=None)
    verified: boolean


class UserUpsertBody(BaseModel):
    address: str


class FilterParams(BaseModel):
    user_id: Optional[str | UUID] = None
    user_address: Optional[str] = None
    page: int = 0
    page_size: int = 15
    search: Optional[str] = None
    audit_type: list[AuditTypeEnum] = Field(default_factory=list)
    status: Optional[AuditStatusEnum] = None
    network: list[NetworkEnum] = Field(default_factory=list)
    contract_address: Optional[str] = None

    @field_validator("audit_type", mode="before")
    @classmethod
    def parse_audit_to_list(cls, value: list[str] | str):
        if not value:
            return []
        if isinstance(value, str):
            return value.split(",")
        return value

    @field_validator("network", mode="before")
    @classmethod
    def parse_network_to_list(cls, value: list[str] | str):
        if not value:
            return []
        if isinstance(value, str):
            return value.split(",")
        return value

    @field_serializer("user_id")
    def convert_uuid_to_string(self, id):
        if isinstance(id, UUID):
            return str(id)
        return id


class ContractScanBody(BaseModel):
    address: Optional[str] = Field(default=None, description="contract address to scan")
    network: Optional[NetworkEnum] = Field(
        default=None, description="network that the contract address is on"
    )
    code: Optional[str] = Field(default=None, description="raw contract code to upload")

    @model_validator(mode="after")
    def validate_params(self):
        if not self.code and not self.address:
            raise ValueError("must provide at least one of address or code")

        if self.network:
            if not self.address and not self.code:
                raise ValueError(
                    "when using network, you must provide the address or code"
                )
        return self
