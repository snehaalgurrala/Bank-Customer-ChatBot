from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="customer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    loan_applications: Mapped[list["LoanApplication"]] = relationship(back_populates="user")
    chatbot_logs: Mapped[list["ChatbotLog"]] = relationship(back_populates="user")
    admin_reviews: Mapped[list["AdminReview"]] = relationship(
        back_populates="admin",
        foreign_keys="AdminReview.admin_id",
    )


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    loan_type: Mapped[str] = mapped_column(String(60), nullable=False)
    loan_amount: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_income: Mapped[float] = mapped_column(Float, nullable=False)
    employment_type: Mapped[str] = mapped_column(String(80), nullable=False)
    existing_emi: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    application_status: Mapped[str] = mapped_column(String(40), default="submitted", nullable=False)
    credit_decision: Mapped[str | None] = mapped_column(String(60), nullable=True)
    approved_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="loan_applications")
    documents: Mapped[list["Document"]] = relationship(back_populates="application")
    admin_reviews: Mapped[list["AdminReview"]] = relationship(back_populates="application")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("loan_applications.id"),
        nullable=True,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    application: Mapped[LoanApplication | None] = relationship(back_populates="documents")


class ChatbotLog(Base):
    __tablename__ = "chatbot_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    bot_response: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User | None] = relationship(back_populates="chatbot_logs")


class AdminReview(Base):
    __tablename__ = "admin_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("loan_applications.id"), nullable=False, index=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(60), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    application: Mapped[LoanApplication] = relationship(back_populates="admin_reviews")
    admin: Mapped[User] = relationship(back_populates="admin_reviews", foreign_keys=[admin_id])
