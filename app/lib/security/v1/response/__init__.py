from pydantic import BaseModel, Field


class FindingType(BaseModel):
    name: str = Field(description="Name of the vulnerability or finding")
    explanation: str = Field(
        description="Description of the vulnerability, with code references if applicable"
    )
    recommendation: str = Field(
        description="Recommended action to take to resolve the vulnerability"
    )
    reference: str = Field(
        description="A reference to the line of code and variable/function related to the vulnerability"
    )


class FindingsStructure(BaseModel):
    critical: list[FindingType] = Field(
        description="A list of critical vulnerabilities, if any"
    )
    high: list[FindingType] = Field(
        description="A list of high severity vulnerabilities, if any"
    )
    medium: list[FindingType] = Field(
        description="A list of medium severity vulnerabilities, if any"
    )
    low: list[FindingType] = Field(
        description="A list of low severity vulnerabilities, if any"
    )


class OutputStructure(BaseModel):
    introduction: str = Field(
        description="a brief introduction of the smart contract's function"
    )
    scope: str = Field(
        description="a brief overview of the scope of the smart contract audit"
    )
    findings: FindingsStructure = Field(
        description="a detailed object of vulnerability findings"
    )
    conclusion: str = Field(description="a brief summary of the audit report")
