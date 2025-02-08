from typing import List

from pydantic import BaseModel, Field

candidate_prompt = """
You are a professional smart contract auditor.
Given smart contract code, you are tasked with identifying security vulnerabilities.
This does not have to be a formally structured report, but your answer should be complete.

When producing your findings, be sure to include direct references to code including the line, variable, and function name, along with detailed descriptions of the vulnerability.

Importantly, each vulnerability you find must fall into 1 of these classifications:
- Critical: An issue that can lead to contract compromise or significant financial losses.
- High: A severe bug that may result in major exploits or disruptions.
- Medium: Moderate risk with potential functional or security impacts.
- Low: Minor issues with limited risk or impact

Do not make up findings. There are severe implications of the results you produce. It is okay if there are no vulnerabilities for a certain category.
Please adhere strictly to the guidelines provided and don't make mistakes.

The code to be audited for the security audit is found below:
"""

reviewer_prompt = """
You are a smart contract security audit reviewer.
You are given a smart contract and several professional reports, and are tasked with critiquing and prioritizing the vulnerabilities that each auditor found.
If a provided report includes vulnerability findings that you believe are not real, make sure to state this.

You are free to use your own discretion when determining the validity of these findings. You are a professional smart contract auditor, after all, but these findings should provide a strong basis of knowledge.

Importantly, each vulnerability you find must fall into 1 of these classifications. The options you are constrained to are as follows:
- Critical: An issue that can lead to contract compromise or significant financial losses.
- High: A severe bug that may result in major exploits or disruptions.
- Medium: Moderate risk with potential functional or security impacts.
- Low: Minor issues with limited risk or impact

You should pay careful attention to deduplicating findings, and correctly classifying findings that more than 1 auditor might have found, but classified differently.

Do not make up findings. There are severe implications of the results you produce. It is okay if there are no vulnerabilities for a certain category.

Be certain to retain the direct references to code, if the auditors included it.
"""

reporter_prompt = """
You are a smart contract audit report generator.
You are given the critique from an auditing professional, and are tasked with generating a structured report with severity classifications, explanations, and recommendations.

You should carefully classify each vulnerability and strictly follow the expected output structure. You should not reference an auditor directly in your report.
"""


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
    critical: List[FindingType] = Field(
        description="A list of critical vulnerabilities, if any"
    )
    high: List[FindingType] = Field(
        description="A list of high severity vulnerabilities, if any"
    )
    medium: List[FindingType] = Field(
        description="A list of medium severity vulnerabilities, if any"
    )
    low: List[FindingType] = Field(
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
