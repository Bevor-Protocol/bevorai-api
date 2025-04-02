from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.utils.schema.models import ContractSchema
from app.utils.types.enums import NetworkEnum

"""
Used for HTTP request validation, response Serialization, and arbitrary typing.
"""


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


class UploadContractResponse(BaseModel):
    exists: bool = Field(
        description="whether at least 1 contract was found with source code"
    )
    exact_match: bool = Field(
        description="whether there is only 1 candidate contract with source code available"  # noqa
    )
    contract: Optional[ContractSchema] = Field(
        default=None, description="contract information, if available"
    )


class StaticAnalysisTokenResult(BaseModel):
    is_mintable: bool = Field(
        description="Whether the token contract has minting capabilities"
    )
    is_honeypot: bool = Field(
        description="Whether the token contract exhibits honeypot characteristics"
    )
    can_steal_fees: bool = Field(
        description="Whether the token contract has functions that could be used to steal fees"  # noqa
    )
    can_self_destruct: bool = Field(
        description="Whether the token contract contains self-destruct functionality"
    )
    has_proxy_functions: bool = Field(
        description="Whether the token contract contains proxy/delegation functions"
    )
    has_allowlist: bool = Field(
        description="Whether the token contract implements allowlist functionality"
    )
    has_blocklist: bool = Field(
        description="Whether the token contract implements blocklist functionality"
    )
    can_terminate_transactions: bool = Field(
        description="Whether the token contract can terminate transactions"
    )
