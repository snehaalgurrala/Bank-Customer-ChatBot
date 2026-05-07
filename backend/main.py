from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.schemas import (
    ChatRequest,
    ChatResponse,
    CreditDecisionUpdate,
    DocumentRead,
    DocumentVerificationUpdate,
    HealthResponse,
    LoanApplicationCreate,
    LoanApplicationRead,
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserRead,
)
from database.models import AdminReview, ChatbotLog, Document, LoanApplication, User
from database.seed import seed_demo_data
from database.session import SessionLocal, get_db, init_db
from utils.config import get_settings
from utils.openrouter_client import OpenRouterError, chat_completion
from utils.rag import index_file, index_sample_data, retrieve_context
from utils.security import TokenError, create_access_token, decode_access_token, hash_password, verify_password

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(title=settings.app_name, version="0.2.0")
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


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (TokenError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token user no longer exists")
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


def _token_response(user: User) -> TokenResponse:
    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(access_token=token, user=user)


@app.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = User(
        name=payload.name,
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role="customer",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered") from exc
    db.refresh(user)
    return _token_response(user)


@app.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return _token_response(user)


@app.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def _calculate_risk_score(payload: LoanApplicationCreate) -> float:
    emi_ratio = payload.existing_emi / max(payload.monthly_income, 1)
    amount_ratio = payload.loan_amount / max(payload.monthly_income * 12, 1)
    risk_score = min(0.95, (emi_ratio * 0.55) + (amount_ratio * 0.25))
    return round(risk_score, 2)


@app.post("/loan-applications", response_model=LoanApplicationRead, status_code=status.HTTP_201_CREATED)
def create_loan_application(
    payload: LoanApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoanApplication:
    application = LoanApplication(
        user_id=current_user.id,
        loan_type=payload.loan_type,
        loan_amount=payload.loan_amount,
        monthly_income=payload.monthly_income,
        employment_type=payload.employment_type,
        existing_emi=payload.existing_emi,
        application_status="submitted",
        credit_decision="pending",
        risk_score=_calculate_risk_score(payload),
        remarks=payload.remarks,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@app.get("/loan-applications", response_model=list[LoanApplicationRead])
def get_user_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LoanApplication]:
    return (
        db.query(LoanApplication)
        .filter(LoanApplication.user_id == current_user.id)
        .order_by(LoanApplication.created_at.desc())
        .all()
    )


@app.get("/loan-applications/{application_id}", response_model=LoanApplicationRead)
def get_application_by_id(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoanApplication:
    application = db.get(LoanApplication, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if current_user.role != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Application access denied")
    return application


@app.post(
    "/loan-applications/{application_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    application_id: int,
    request: Request,
    x_filename: str = Header(..., alias="X-Filename"),
    x_document_type: str = Header("supporting_document", alias="X-Document-Type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    application = db.get(LoanApplication, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if current_user.role != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Application access denied")

    suffix = Path(x_filename).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported document type")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    safe_name = Path(x_filename).name
    stored_name = f"application_{application_id}_{uuid4().hex}_{safe_name}"
    destination = settings.upload_dir / stored_name
    destination.write_bytes(body)

    indexed_chunks = 0
    if suffix in {".txt", ".md", ".pdf"}:
        try:
            indexed_chunks = index_file(destination)
        except ValueError:
            indexed_chunks = 0

    document = Document(
        application_id=application.id,
        document_type=x_document_type,
        file_path=str(destination),
        verification_status="pending",
        remarks=f"Uploaded locally. Indexed chunks: {indexed_chunks}.",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@app.get("/loan-applications/{application_id}/documents", response_model=list[DocumentRead])
def get_documents_for_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Document]:
    application = db.get(LoanApplication, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if current_user.role != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Application access denied")
    return (
        db.query(Document)
        .filter(Document.application_id == application_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


@app.get("/admin/applications", response_model=list[LoanApplicationRead])
def admin_view_all_applications(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[LoanApplication]:
    return db.query(LoanApplication).order_by(LoanApplication.created_at.desc()).all()


@app.patch("/admin/documents/{document_id}/verification", response_model=DocumentRead)
def admin_update_document_verification_status(
    document_id: int,
    payload: DocumentVerificationUpdate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document.verification_status = payload.verification_status
    document.remarks = payload.remarks
    db.commit()
    db.refresh(document)
    return document


@app.patch("/admin/applications/{application_id}/credit-decision", response_model=LoanApplicationRead)
def admin_update_credit_decision(
    application_id: int,
    payload: CreditDecisionUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> LoanApplication:
    application = db.get(LoanApplication, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    application.credit_decision = payload.credit_decision
    if payload.application_status:
        application.application_status = payload.application_status
    if payload.risk_score is not None:
        application.risk_score = payload.risk_score
    if payload.remarks is not None:
        application.remarks = payload.remarks
    db.add(
        AdminReview(
            application_id=application.id,
            admin_id=current_admin.id,
            decision=payload.credit_decision,
            remarks=payload.remarks,
        )
    )
    db.commit()
    db.refresh(application)
    return application


@app.post("/chatbot", response_model=ChatResponse)
def chatbot(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    context, sources = retrieve_context(payload.message)
    history_rows = (
        db.query(ChatbotLog)
        .filter(ChatbotLog.user_id == current_user.id)
        .order_by(ChatbotLog.timestamp.desc())
        .limit(4)
        .all()
    )
    conversation: list[dict[str, str]] = []
    for row in reversed(history_rows):
        conversation.append({"role": "user", "content": row.message})
        conversation.append({"role": "assistant", "content": row.bot_response})
    try:
        answer = chat_completion(payload.message, context=context, conversation=conversation)
    except OpenRouterError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    db.add(ChatbotLog(user_id=current_user.id, message=payload.message, bot_response=answer))
    db.commit()
    return ChatResponse(answer=answer, sources=sources)


@app.post("/documents/index-samples")
def index_samples(_: User = Depends(get_current_admin)) -> dict[str, int]:
    chunks = index_sample_data()
    return {"indexed_chunks": chunks}
