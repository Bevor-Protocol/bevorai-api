from pydantic import BaseModel, Field


class StaticAnalysisTokenResult(BaseModel):
    is_mintable: bool = Field(description="Whether the token contract has minting capabilities")
    is_honeypot: bool = Field(description="Whether the token contract exhibits honeypot characteristics")
    can_steal_fees: bool = Field(description="Whether the token contract has functions that could be used to steal fees")
    can_self_destruct: bool = Field(description="Whether the token contract contains self-destruct functionality")
    has_proxy_functions: bool = Field(description="Whether the token contract contains proxy/delegation functions")
    has_allowlist: bool = Field(description="Whether the token contract implements allowlist functionality")
    has_blocklist: bool = Field(description="Whether the token contract implements blocklist functionality") 
    can_terminate_transactions: bool = Field(description="Whether the token contract can terminate transactions")

