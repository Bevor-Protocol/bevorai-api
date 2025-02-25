from typing import Optional

from pydantic import Field

from app.utils.enums import ContractMethodEnum, NetworkEnum

from .shared import IdResponse


class ContractPydantic(IdResponse):
    method: ContractMethodEnum = Field(
        description="method used to upload contract code"
    )
    address: Optional[str] = Field(
        default=None, description="contract address, if applicable"
    )
    network: Optional[NetworkEnum] = Field(
        default=None, description="network that the contract is on, if applicable"
    )
    is_available: bool = Field(description="whether source code is available")


class ContractWithCodePydantic(ContractPydantic):
    code: Optional[str] = Field(
        default=None, description="raw smart contract code, if found"
    )
