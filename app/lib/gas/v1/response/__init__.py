from pydantic import BaseModel, Field


class FindingType(BaseModel):
    name: str = Field(description="Name of the gas optimization finding")
    explanation: str = Field(
        description="Description of the gas optimization, with code references if applicable"
    )
    recommendation: str = Field(
        description="Recommended action to take to resolve the gas optimization"
    )
    reference: str = Field(
        description="A reference to the line of code and variable/function related to the gas optimization"
    )


class FindingsStructure(BaseModel):
    critical: list[FindingType] = Field(
        description="A list of critical gas optimizations, if any"
    )
    high: list[FindingType] = Field(
        description="A list of high severity gas optimizations, if any"
    )
    medium: list[FindingType] = Field(
        description="A list of medium severity gas optimizations, if any"
    )
    low: list[FindingType] = Field(
        description="A list of low severity gas optimizations, if any"
    )


class OutputStructure(BaseModel):
    introduction: str = Field(
        description="a brief introduction of the smart contract's function"
    )
    scope: str = Field(
        description="a brief overview of the scope of the smart contract audit"
    )
    findings: FindingsStructure = Field(
        description="a detailed object of gas optimization findings"
    )
    conclusion: str = Field(description="a brief summary of the audit report")
