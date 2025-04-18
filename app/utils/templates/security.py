security_template = """
# Smart Contract Security Audit Report

---

Produced by: BevorAI Agent
> 🛑 Disclaimer: This report is generated by the BevorAI Agent, an experimental AI-based auditing tool. While every effort is made to ensure accuracy, this report should not replace a professional, human audit.

---

⚠️ Severity Level Definitions
- Critical: 🚨 Issues that can lead to contract compromise or significant financial losses.
- High: 🔴 Severe bugs that may result in major exploits or disruptions.
- Medium: 🟠 Moderate risks with potential functional or security impacts.
- Low: 🟢 Minor issues with limited risk or impact.

---

## 📝 Audit Summary
- Contract Address: {address}
- Audit Date: {date}
- Auditor: BevorAI Agent

---

## 🧐 Introduction
{introduction}

---

## 🔍 Audit Scope
{scope}

---

## 🛠 Findings

### 🚨 Critical
{findings_critical}

### 🔴 High
{findings_high}

### 🟠 Medium
{findings_medium}

### 🟢 Low
{findings_low}


---

## ✅ Conclusion
{conclusion}
"""
