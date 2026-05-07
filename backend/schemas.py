from datetime import datetime

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=180)
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=180)
    password: str


class UserRead(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class LoanApplicationCreate(BaseModel):
    loan_type: str = Field(min_length=2, max_length=60)
    loan_amount: float = Field(gt=0)
    monthly_income: float = Field(gt=0)
    employment_type: str = Field(min_length=2, max_length=80)
    existing_emi: float = Field(default=0, ge=0)
    remarks: str | None = None


class EligibilityRequest(BaseModel):
    monthly_income: float = Field(gt=0)
    existing_emi: float = Field(default=0, ge=0)
    loan_amount: float = Field(gt=0)
    employment_type: str = Field(min_length=2, max_length=80)
    missing_documents: int = Field(default=0, ge=0)


class EligibilityResponse(BaseModel):
    disposable_income: float
    emi_capacity: float
    eligible_amount: float
    risk_score: float
    risk_level: str
    recommendation: str


class LoanApplicationRead(LoanApplicationCreate):
    id: int
    user_id: int
    application_status: str
    credit_decision: str | None
    risk_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: int
    application_id: int | None
    document_type: str
    file_path: str
    verification_status: str
    remarks: str | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentVerificationUpdate(BaseModel):
    verification_status: str = Field(min_length=2, max_length=40)
    remarks: str | None = None


class CreditDecisionUpdate(BaseModel):
    credit_decision: str = Field(min_length=2, max_length=60)
    application_status: str | None = Field(default=None, max_length=40)
    risk_score: float | None = Field(default=None, ge=0, le=1)
    remarks: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=2)
    application_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, str]] = []


class HealthResponse(BaseModel):
    status: str
    app_name: str
