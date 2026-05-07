from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from database.models import Document, LoanApplication, User
from utils.eligibility import calculate_eligibility

REQUIRED_DOCUMENTS = {
    "identity_proof": "Government-issued identity proof",
    "income_proof": "Recent salary slip, tax return, or income proof",
    "bank_statement": "Recent bank statement",
}


def get_user_application(db: Session, user: User, application_id: int | None = None) -> LoanApplication | None:
    query = db.query(LoanApplication)
    if user.role != "admin":
        query = query.filter(LoanApplication.user_id == user.id)
    if application_id is not None:
        return query.filter(LoanApplication.id == application_id).first()
    return query.order_by(LoanApplication.created_at.desc()).first()


def check_application_status(db: Session, user: User, application_id: int | None = None) -> dict[str, Any]:
    application = get_user_application(db, user, application_id)
    if not application:
        return {"found": False, "message": "No loan application was found for this user."}
    return {
        "found": True,
        "application_id": application.id,
        "loan_type": application.loan_type,
        "application_status": application.application_status,
        "credit_decision": application.credit_decision,
        "risk_score": application.risk_score,
        "remarks": application.remarks,
        "created_at": application.created_at.isoformat(),
    }


def check_missing_documents(db: Session, user: User, application_id: int | None = None) -> dict[str, Any]:
    application = get_user_application(db, user, application_id)
    if not application:
        return {"found": False, "message": "No loan application was found for this user."}
    documents = db.query(Document).filter(Document.application_id == application.id).all()
    uploaded_types = {document.document_type for document in documents}
    verified_types = {
        document.document_type
        for document in documents
        if document.verification_status.lower() == "verified"
    }
    missing = [
        {"document_type": doc_type, "description": description}
        for doc_type, description in REQUIRED_DOCUMENTS.items()
        if doc_type not in uploaded_types
    ]
    unverified = [
        {
            "document_id": document.id,
            "document_type": document.document_type,
            "verification_status": document.verification_status,
            "remarks": document.remarks,
        }
        for document in documents
        if document.document_type in REQUIRED_DOCUMENTS and document.document_type not in verified_types
    ]
    return {
        "found": True,
        "application_id": application.id,
        "required_documents": REQUIRED_DOCUMENTS,
        "uploaded_document_types": sorted(uploaded_types),
        "missing_documents": missing,
        "unverified_documents": unverified,
        "missing_count": len(missing),
    }


def calculate_application_eligibility(
    db: Session,
    user: User,
    application_id: int | None = None,
    requested_loan_amount: float | None = None,
) -> dict[str, Any]:
    application = get_user_application(db, user, application_id)
    if not application:
        return {"found": False, "message": "No loan application was found for this user."}
    missing = check_missing_documents(db, user, application.id)
    eligibility = calculate_eligibility(
        monthly_income=application.monthly_income,
        existing_emi=application.existing_emi,
        loan_amount=requested_loan_amount or application.loan_amount,
        employment_type=application.employment_type,
        missing_documents=missing.get("missing_count", 0),
    )
    return {
        "found": True,
        "application_id": application.id,
        "loan_amount": requested_loan_amount or application.loan_amount,
        "stored_application_amount": application.loan_amount,
        "monthly_income": application.monthly_income,
        "existing_emi": application.existing_emi,
        "employment_type": application.employment_type,
        **eligibility,
    }


def get_credit_decision(db: Session, user: User, application_id: int | None = None) -> dict[str, Any]:
    application = get_user_application(db, user, application_id)
    if not application:
        return {"found": False, "message": "No loan application was found for this user."}
    documents = db.query(Document).filter(Document.application_id == application.id).all()
    missing = check_missing_documents(db, user, application.id)
    return {
        "found": True,
        "application_id": application.id,
        "loan_type": application.loan_type,
        "requested_amount": application.loan_amount,
        "approved_amount": application.approved_amount,
        "monthly_income": application.monthly_income,
        "existing_emi": application.existing_emi,
        "employment_type": application.employment_type,
        "credit_decision": application.credit_decision or "pending",
        "application_status": application.application_status,
        "risk_score": application.risk_score,
        "remarks": application.remarks,
        "documents": [
            {
                "document_id": document.id,
                "document_type": document.document_type,
                "verification_status": document.verification_status,
                "remarks": document.remarks,
            }
            for document in documents
        ],
        "missing_documents": missing.get("missing_documents", []),
    }
