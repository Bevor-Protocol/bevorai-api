from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.utils.enums import AuditTypeEnum, PlatformEnum


class EvalBody(BaseModel):
    contract_code: Optional[str] = Field(default=None)
    contract_address: Optional[str] = Field(default=None)
    contract_network: Optional[PlatformEnum] = Field(default=None)
    audit_type: AuditTypeEnum = Field(default=AuditTypeEnum.GAS)
    webhook_url: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def validate_contract_inputs(self) -> "EvalBody":
        if not self.contract_code and not self.contract_address:
            raise ValueError(
                "Either contract_code or contract_address must be provided"
            )

        if self.contract_address and not self.network:
            raise ValueError("network is required when contract_address is provided")

        return self
