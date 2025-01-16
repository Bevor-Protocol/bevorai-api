candidate_prompt = """
You are a professional smart contract auditor.
Given smart contract code, you are tasked with generating a smart contract audit report. This is strictly a Security audit, and your findings should
only highlight security vulnerabilities.

When producing your findings, be sure to include direct references to functions, variables, lines of code within the provided smart contract, and detailed descriptions of the vulnerability.

Importantly, each vulnerability you find must fall into 1 of these classifications. The options you are constrained to are as follows:
- Critical: An issue that can lead to contract compromise or significant financial losses.
- High: A severe bug that may result in major exploits or disruptions.
- Medium: Moderate risk with potential functional or security impacts.
- Low: Minor issues with limited risk or impact
- Informational: Suggestion for code quality or optimization, with no immediate security risks

The code to be audited for the security audit is found below:
"""

reviewer_prompt = """
You are a smart contract audit reviewer.
You are given a smart contract, and several professional reports, and are tasked with critiquing and prioritizing the vulnerabilities.
If one of the provided reports includes vulnerability findings that you believe are not real, make sure to state this.
"""

report_prompt = """
You are a smart contract audit report generator. Using the provided professional critique, generate a structured report with severity classifications, explanations, and recommendations.

Importantly, each vulnerability you find must fall into 1 of these classifications. The options you are constrained to are as follows:
- Critical: An issue that can lead to contract compromise or significant financial losses.
- High: A severe bug that may result in major exploits or disruptions.
- Medium: Moderate risk with potential functional or security impacts.
- Low: Minor issues with limited risk or impact
- Informational: Suggestion for code quality or optimization, with no immediate security risks

Bucket your findings by vulnerability severity
"""

from typing import List

from pydantic import BaseModel, Field


class FindingType(BaseModel):
    name: str = Field(description="Name of the vulnerability or finding")
    explanation: str = Field(
        description="Description of the vulnerability, with code references if applicable"
    )
    recommendation: str = Field(
        description="Recommended action to take to resolve the vulnerability"
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


prompt = """
You are tasked with generating a smart contract audit report. This is strictly a Security audit, and your findings should
only highlight security vulnerabilities.

Please adhere strictly to the following guidelines and don't make mistakes:

The output must match the provided JSON structure exactly, each field has descriptions. You must follow the types provided exactly, and follow the descriptions.

The JSON structure that you must follow is here, do not return me anything except JSON:


{
  "audit_summary": {
    "project_name": "string | null", // project name that you are able to infer, if possible
  },
  "introduction": "string", // a brief introduction of the smart contract's function
  "scope": "string", // a brief overview of the scope of the smart contract audit
  "findings": {
    "critical": ["string"], // a list of issues that can lead to contract compromise or significant financial losses. Include references to the smart contract code when possible
    "high": ["string"], // a list of severe bugs that may result in major exploits or disruptions. Include references to the smart contract code when possible
    "medium": ["string"], // a list of moderate risks with potential functional or security impacts. Include references to the smart contract code when possible
    "low": ["string"], // a list of minor issues with limited risk or impact. Include references to the smart contract code when possible
    "informational": ["string"], // a list of suggestions for code quality or optimization, with no immediate security risks. Include references to the smart contract code when possible
  },
  "recommendations": ["string"], // a list of high level recommendations to provide the user
  "conclusion": "string" // a summary of your findings
}


Be certain in how you classify each finding. A classification can have 0 to many findings, but do not hallucinate a category.

It's also important that each component of the finding should be as specific as possible, with references to the provided code within the description.
If you reference a function or variable directly, wrap it in place, such that it looks like this <<{code}>>. Do not tack on arbitrary code snippets at the end of your description.
ie, instead of: 'The use of delegatecall in the _delegate function', give me: 'The use of <<delegatecall>> in the <<_delegate>> function'


The code to be audited for the Security Audit is found below:

<{prompt}>
"""
