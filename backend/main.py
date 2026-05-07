from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.schemas import (
    ChatRequest,
    ChatResponse,
    CustomerCreate,
    CustomerRead,
    DocumentRead,
    HealthResponse,
    LoanApplicationCreate,
    LoanApplicationRead,
)
from database.models import ChatMessage, Customer, LoanApplication, UploadedDocument
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


@app.post("/customers", response_model=CustomerRead)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> Customer:
    existing = db.query(Customer).filter(Customer.email == payload.email).first()
    if existing:
        return existing
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@app.post("/loan-applications", response_model=LoanApplicationRead)
def create_loan_application(payload: LoanApplicationCreate, db: Session = Depends(get_db)) -> LoanApplication:
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    application = LoanApplication(**payload.model_dump(), status="submitted")
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@app.get("/loan-applications/{customer_id}", response_model=list[LoanApplicationRead])
def list_loan_applications(customer_id: int, db: Session = Depends(get_db)) -> list[LoanApplication]:
    return (
        db.query(LoanApplication)
        .filter(LoanApplication.customer_id == customer_id)
        .order_by(LoanApplication.created_at.desc())
        .all()
    )


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    if payload.customer_id and not db.get(Customer, payload.customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")

    db.add(ChatMessage(customer_id=payload.customer_id, role="user", content=payload.message))
    db.commit()

    context, sources = retrieve_context(payload.message)
    history_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.customer_id == payload.customer_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(8)
        .all()
    )
    conversation = [{"role": row.role, "content": row.content} for row in reversed(history_rows)]
    try:
        answer = chat_completion(payload.message, context=context, conversation=conversation)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    db.add(ChatMessage(customer_id=payload.customer_id, role="assistant", content=answer))
    db.commit()
    return ChatResponse(answer=answer, sources=sources)


@app.post("/documents/upload", response_model=DocumentRead)
async def upload_document(
    request: Request,
    x_filename: str = Header(..., alias="X-Filename"),
    x_content_type: str | None = Header(None, alias="X-Content-Type"),
    db: Session = Depends(get_db),
) -> UploadedDocument:
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

    document = UploadedDocument(
        filename=safe_name,
        stored_path=str(destination),
        content_type=x_content_type,
        indexed_chunks=chunks,
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
def list_documents(db: Session = Depends(get_db)) -> list[UploadedDocument]:
    return db.query(UploadedDocument).order_by(UploadedDocument.created_at.desc()).all()
