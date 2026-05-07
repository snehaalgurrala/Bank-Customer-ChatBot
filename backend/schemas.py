from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=180)
    phone: str | None = None
    password_hash: str = "pbkdf2:demo-password-hash"
    role: str = "customer"


class UserRead(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoanApplicationCreate(BaseModel):
    user_id: int
    loan_type: str = Field(min_length=2, max_length=60)
    loan_amount: float = Field(gt=0)
    monthly_income: float = Field(gt=0)
    employment_type: str = Field(min_length=2, max_length=80)
    existing_emi: float = Field(default=0, ge=0)
    remarks: str | None = None


class LoanApplicationRead(LoanApplicationCreate):
    id: int
    application_status: str
    credit_decision: str | None
    risk_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(min_length=2)
    user_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, str]] = []


class DocumentRead(BaseModel):
    id: int
    application_id: int | None
    document_type: str
    file_path: str
    verification_status: str
    remarks: str | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class AdminReviewRead(BaseModel):
    id: int
    application_id: int
    admin_id: int
    decision: str
    remarks: str | None
    reviewed_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    app_name: str
