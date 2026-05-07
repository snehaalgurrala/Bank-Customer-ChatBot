from sqlalchemy.orm import Session

from database.models import AdminReview, ChatbotLog, Document, LoanApplication, User
from utils.security import hash_password


ADMIN_EMAIL = "admin@loanbot.local"
CUSTOMER_EMAIL = "demo.customer@example.com"


def seed_demo_data(db: Session) -> None:
    admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if not admin:
        admin = User(
            name="Loan Review Admin",
            email=ADMIN_EMAIL,
            phone="+1-555-0199",
            password_hash=hash_password("AdminPass123!"),
            role="admin",
        )
        db.add(admin)
        db.flush()
    elif not admin.password_hash.startswith("pbkdf2_sha256$"):
        admin.password_hash = hash_password("AdminPass123!")

    customer = db.query(User).filter(User.email == CUSTOMER_EMAIL).first()
    if not customer:
        customer = User(
            name="Demo Customer",
            email=CUSTOMER_EMAIL,
            phone="+1-555-0100",
            password_hash=hash_password("CustomerPass123!"),
            role="customer",
        )
        db.add(customer)
        db.flush()
    elif not customer.password_hash.startswith("pbkdf2_sha256$"):
        customer.password_hash = hash_password("CustomerPass123!")

    application = (
        db.query(LoanApplication)
        .filter(LoanApplication.user_id == customer.id, LoanApplication.loan_type == "Personal Loan")
        .first()
    )
    if not application:
        application = LoanApplication(
            user_id=customer.id,
            loan_type="Personal Loan",
            loan_amount=15000,
            monthly_income=6000,
            employment_type="Salaried",
            existing_emi=450,
            application_status="under_review",
            credit_decision="manual_review_required",
            risk_score=0.34,
            remarks="Seed application for validating customer loan assistance workflows.",
        )
        db.add(application)
        db.flush()

    policy_document = (
        db.query(Document)
        .filter(Document.file_path == "sample_data/loan_policy.md")
        .first()
    )
    if not policy_document:
        db.add(
            Document(
                application_id=application.id,
                document_type="sample_loan_policy",
                file_path="sample_data/loan_policy.md",
                verification_status="verified",
                remarks="Sample policy data used by the chatbot knowledge base.",
            )
        )

    existing_log = (
        db.query(ChatbotLog)
        .filter(ChatbotLog.user_id == customer.id, ChatbotLog.message == "What documents are needed for a loan?")
        .first()
    )
    if not existing_log:
        db.add(
            ChatbotLog(
                user_id=customer.id,
                message="What documents are needed for a loan?",
                bot_response="Typical documents include identity proof, income proof, bank statements, and loan-specific documents.",
            )
        )

    existing_review = (
        db.query(AdminReview)
        .filter(AdminReview.application_id == application.id, AdminReview.admin_id == admin.id)
        .first()
    )
    if not existing_review:
        db.add(
            AdminReview(
                application_id=application.id,
                admin_id=admin.id,
                decision="needs_documents",
                remarks="Request latest bank statement and income proof before final decision.",
            )
        )

    db.commit()
