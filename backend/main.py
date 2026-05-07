from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.schemas import (
    AdminReviewRead,
    ChatRequest,
    ChatResponse,
    DocumentRead,
    HealthResponse,
    LoanApplicationCreate,
    LoanApplicationRead,
    UserCreate,
    UserRead,
)
from database.models import AdminReview, ChatbotLog, Document, LoanApplication, User
from database.seed import seed_demo_data
from database.session import SessionLocal, get_db, init_db
from utils.config import get_settings
from utils.openrouter_client import OpenRouterError, chat_completion
from utils.rag import index_file, index_sample_data, retrieve_context

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    with SessionLocal() as db:
        seed_demo_data(db)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name)


@app.post("/users", response_model=UserRead)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        return existing
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/customers", response_model=UserRead)
def create_customer(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    return create_user(payload, db)


@app.post("/loan-applications", response_model=LoanApplicationRead)
def create_loan_application(payload: LoanApplicationCreate, db: Session = Depends(get_db)) -> LoanApplication:
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    application = LoanApplication(
        **payload.model_dump(),
        application_status="submitted",
        credit_decision="pending",
        risk_score=_calculate_risk_score(payload),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def _calculate_risk_score(payload: LoanApplicationCreate) -> float:
    emi_ratio = payload.existing_emi / max(payload.monthly_income, 1)
    amount_ratio = payload.loan_amount / max(payload.monthly_income * 12, 1)
    risk_score = min(0.95, (emi_ratio * 0.55) + (amount_ratio * 0.25))
    return round(risk_score, 2)


@app.get("/loan-applications/{user_id}", response_model=list[LoanApplicationRead])
def list_loan_applications(user_id: int, db: Session = Depends(get_db)) -> list[LoanApplication]:
    return (
        db.query(LoanApplication)
        .filter(LoanApplication.user_id == user_id)
        .order_by(LoanApplication.created_at.desc())
        .all()
    )


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    if payload.user_id and not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")

    context, sources = retrieve_context(payload.message)
    history_rows = db.query(ChatbotLog).filter(ChatbotLog.user_id == payload.user_id).order_by(ChatbotLog.timestamp.desc()).limit(4).all()
    conversation: list[dict[str, str]] = []
    for row in reversed(history_rows):
        conversation.append({"role": "user", "content": row.message})
        conversation.append({"role": "assistant", "content": row.bot_response})
    try:
        answer = chat_completion(payload.message, context=context, conversation=conversation)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    db.add(ChatbotLog(user_id=payload.user_id, message=payload.message, bot_response=answer))
    db.commit()
    return ChatResponse(answer=answer, sources=sources)


@app.post("/documents/upload", response_model=DocumentRead)
async def upload_document(
    request: Request,
    x_filename: str = Header(..., alias="X-Filename"),
    x_content_type: str | None = Header(None, alias="X-Content-Type"),
    db: Session = Depends(get_db),
) -> Document:
    suffix = Path(x_filename).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf"}:
        raise HTTPException(status_code=400, detail="Only .txt, .md, and .pdf files are supported")

    safe_name = Path(x_filename).name
    destination = settings.upload_dir / safe_name
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    with destination.open("wb") as buffer:
        buffer.write(body)

    try:
        chunks = index_file(destination)
    except ValueError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document = Document(
        application_id=None,
        document_type=x_content_type or suffix.removeprefix("."),
        file_path=str(destination),
        verification_status="indexed",
        remarks=f"Indexed {chunks} chunks for chatbot retrieval.",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@app.post("/documents/index-samples")
def index_samples() -> dict[str, int]:
    chunks = index_sample_data()
    return {"indexed_chunks": chunks}


@app.get("/documents", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


@app.get("/admin-reviews", response_model=list[AdminReviewRead])
def list_admin_reviews(db: Session = Depends(get_db)) -> list[AdminReview]:
    return db.query(AdminReview).order_by(AdminReview.reviewed_at.desc()).all()
