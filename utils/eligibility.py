from __future__ import annotations

from typing import Any


EMPLOYMENT_RISK_FACTORS = {
    "salaried": 0.02,
    "self-employed": 0.10,
    "self_employed": 0.10,
    "contract": 0.14,
    "retired": 0.18,
}


def calculate_eligibility(
    monthly_income: float,
    existing_emi: float,
    loan_amount: float,
    employment_type: str,
    missing_documents: int = 0,
) -> dict[str, Any]:
    disposable_income = max(monthly_income - existing_emi, 0)
    emi_capacity = max(monthly_income * 0.40 - existing_emi, 0)
    eligible_amount = round(max(emi_capacity, 0) * 36, 2)

    income_risk = 0.25 if monthly_income < 3000 else 0.15 if monthly_income < 7000 else 0.06
    emi_burden_ratio = existing_emi / monthly_income if monthly_income > 0 else 1
    emi_risk = min(0.30, emi_burden_ratio * 0.60)
    amount_ratio = loan_amount / max(monthly_income * 12, 1)
    amount_risk = min(0.25, amount_ratio * 0.18)
    employment_risk = EMPLOYMENT_RISK_FACTORS.get(employment_type.strip().lower(), 0.12)
    document_risk = min(0.20, missing_documents * 0.05)

    risk_score = round(min(1.0, income_risk + emi_risk + amount_risk + employment_risk + document_risk), 2)
    if risk_score < 0.35:
        risk_level = "Low"
    elif risk_score < 0.65:
        risk_level = "Medium"
    else:
        risk_level = "High"

    if eligible_amount <= 0:
        recommendation = "Not eligible based on current EMI obligations. Reduce existing EMI or add income proof."
    elif loan_amount <= eligible_amount and risk_level == "Low":
        recommendation = "Likely eligible. Proceed with standard document verification."
    elif loan_amount <= eligible_amount and risk_level == "Medium":
        recommendation = "Conditionally eligible. Review documents and repayment history before approval."
    elif loan_amount <= eligible_amount:
        recommendation = "Eligible amount is sufficient, but risk is high. Send for manual credit review."
    else:
        recommendation = "Requested amount exceeds estimated eligibility. Recommend a lower amount or co-applicant."

    return {
        "disposable_income": round(disposable_income, 2),
        "emi_capacity": round(emi_capacity, 2),
        "eligible_amount": eligible_amount,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "recommendation": recommendation,
    }
