from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=180)
    phone: str | None = None


class CustomerRead(CustomerCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LoanApplicationCreate(BaseModel):
    customer_id: int
    loan_type: str = Field(min_length=2, max_length=60)
    amount: float = Field(gt=0)
    annual_income: float = Field(gt=0)
    credit_score: int = Field(ge=300, le=850)
    notes: str | None = None


class LoanApplicationRead(LoanApplicationCreate):
    id: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(min_length=2)
    customer_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, str]] = []


class DocumentRead(BaseModel):
    id: int
    filename: str
    content_type: str | None
    indexed_chunks: int
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    app_name: str
