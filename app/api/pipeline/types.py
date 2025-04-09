# flake8: noqa

from pydantic import BaseModel, Field


class SecurityFindingType(BaseModel):
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


class SecurityFindingsStructure(BaseModel):
    critical: list[SecurityFindingType] = Field(
        description="A list of critical vulnerabilities, if any"
    )
    high: list[SecurityFindingType] = Field(
        description="A list of high severity vulnerabilities, if any"
    )
    medium: list[SecurityFindingType] = Field(
        description="A list of medium severity vulnerabilities, if any"
    )
    low: list[SecurityFindingType] = Field(
        description="A list of low severity vulnerabilities, if any"
    )


class SecurityOutputStructure(BaseModel):
    introduction: str = Field(
        description="a brief introduction of the smart contract's function"
    )
    scope: str = Field(
        description="a brief overview of the scope of the smart contract audit"
    )
    findings: SecurityFindingsStructure = Field(
        description="a detailed object of vulnerability findings"
    )
    conclusion: str = Field(description="a brief summary of the audit report")


class GasFindingType(BaseModel):
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


class GasFindingsStructure(BaseModel):
    critical: list[GasFindingType] = Field(
        description="A list of critical gas optimizations, if any"
    )
    high: list[GasFindingType] = Field(
        description="A list of high severity gas optimizations, if any"
    )
    medium: list[GasFindingType] = Field(
        description="A list of medium severity gas optimizations, if any"
    )
    low: list[GasFindingType] = Field(
        description="A list of low severity gas optimizations, if any"
    )


class GasOutputStructure(BaseModel):
    introduction: str = Field(
        description="a brief introduction of the smart contract's function"
    )
    scope: str = Field(
        description="a brief overview of the scope of the smart contract audit"
    )
    findings: GasFindingsStructure = Field(
        description="a detailed object of gas optimization findings"
    )
    conclusion: str = Field(description="a brief summary of the audit report")
