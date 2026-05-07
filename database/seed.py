from sqlalchemy.orm import Session

from database.models import Customer, LoanApplication


def seed_demo_data(db: Session) -> None:
    existing = db.query(Customer).filter(Customer.email == "demo.customer@example.com").first()
    if existing:
        return

    customer = Customer(
        full_name="Demo Customer",
        email="demo.customer@example.com",
        phone="+1-555-0100",
    )
    db.add(customer)
    db.flush()
    db.add(
        LoanApplication(
            customer_id=customer.id,
            loan_type="Personal Loan",
            amount=15000,
            annual_income=72000,
            credit_score=710,
            status="pre-qualified",
            notes="Demo profile for validating chatbot workflows.",
        )
    )
    db.commit()
