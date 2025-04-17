# flake8: noqa

from pydantic import BaseModel, Field


class FindingType(BaseModel):
    name: str = Field(description="Name of the finding")
    explanation: str = Field(
        description="Description of the finding, with code references if applicable"
    )
    recommendation: str = Field(
        description="Recommended action to take to resolve the finding"
    )
    reference: str = Field(
        description="A reference to the line of code and variable/function related to the finding"
    )


class FindingsStructure(BaseModel):
    critical: list[FindingType] = Field(
        description="A list of critical findings, if any"
    )
    high: list[FindingType] = Field(
        description="A list of high severity findings, if any"
    )
    medium: list[FindingType] = Field(
        description="A list of medium severity findings, if any"
    )
    low: list[FindingType] = Field(
        description="A list of low severity findings, if any"
    )


class OutputStructure(BaseModel):
    introduction: str = Field(
        description="a brief introduction of the smart contract's function"
    )
    scope: str = Field(
        description="a brief overview of the scope of the smart contract audit"
    )
    conclusion: str = Field(description="a brief summary of the audit report")
    findings: FindingsStructure
