# AI Customer Loan Assistance Chatbot

A full-stack Python project for a bank-style customer loan assistance chatbot. The app supports customer signup/login, loan applications, document uploads, admin document review, credit decisions, RAG policy answers, and an agentic chatbot backed by OpenRouter, LangChain, ChromaDB, SQLite, and SQLAlchemy.

## Features

- JWT-based signup and login
- Customer loan application workflow
- Local document upload storage in `uploads/`
- Admin dashboard with status filtering, applicant details, document verification, approved amount, remarks, and credit decisions
- AI credit summary for admins
- Agentic chatbot that routes questions to:
  - RAG policy answer tool
  - Application status tool
  - Missing document checker
  - Eligibility calculator
  - Credit decision explanation tool
- LangChain document loading and chunking
- ChromaDB vector storage and retrieval
- OpenRouter LLM integration with environment-based configuration
- SQLite database with SQLAlchemy models and seed data

## Project Structure

```text
Bank-Customer-ChatBot/
|-- backend/       FastAPI app, auth, API routes, request/response schemas
|-- frontend/      Streamlit multi-page UI for customers and admins
|-- database/      SQLAlchemy models, SQLite session, init and seed scripts
|-- docs/          API and architecture documentation
|-- sample_data/   Loan policy documents used for RAG
|-- uploads/       Local uploaded customer/application documents
|-- utils/         Security, AI service, RAG, eligibility, config helpers
|-- vectorstore/   ChromaDB persisted vector index
|-- requirements.txt
|-- .env.example
`-- README.md
```

## Architecture

```text
Streamlit Frontend
        |
        | requests + JWT bearer token
        v
FastAPI Backend
        |
        | SQLAlchemy ORM
        v
SQLite Database
        |
        | application data, users, documents, chatbot logs
        v
Agentic Chatbot Service
        |---------------------> Database tools
        |                       - status
        |                       - missing documents
        |                       - eligibility
        |                       - credit decision
        |
        |---------------------> LangChain + ChromaDB RAG
        |                       - sample loan policy documents
        |                       - uploaded text/PDF documents
        |
        `---------------------> OpenRouter LLM
```

## Installation

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Create your local environment file.

```powershell
Copy-Item .env.example .env
```

4. Edit `.env`.

```text
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=openai/gpt-4o-mini
JWT_SECRET_KEY=replace-with-a-long-random-secret
```

The chatbot can still run with local fallback responses if `OPENROUTER_API_KEY` is not configured.

5. Initialize the SQLite database and seed demo data.

```powershell
python -m database.init_db
```

For an older local development database, rebuild the tables:

```powershell
python -m database.init_db --reset
```

## Run the Backend

```powershell
uvicorn backend.main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Run the Frontend

Open a second terminal and run:

```powershell
streamlit run frontend/app.py
```

Streamlit usually opens:

```text
http://localhost:8501
```

## Sample Login Credentials

```text
Customer: demo.customer@example.com / CustomerPass123!
Admin:    admin@loanbot.local       / AdminPass123!
```

## First Use

1. Start the backend with `uvicorn backend.main:app --reload`.
2. Start the frontend with `streamlit run frontend/app.py`.
3. Log in as the admin and click `Index sample knowledge`.
4. Log in as the customer to submit an application and upload documents.
5. Use the admin dashboard to review documents and update credit decisions.
6. Ask the chatbot questions such as:
   - `What documents are required?`
   - `What is my loan status?`
   - `Which document is missing?`
   - `Am I eligible for 5 lakh loan?`

## Validation and Error Handling

- FastAPI validates request bodies with Pydantic schemas.
- Protected APIs require JWT bearer authentication.
- Admin-only APIs check the user role before processing.
- Upload APIs validate file extension and empty files.
- Ownership checks prevent customers from reading other users' applications.
- API errors are returned with clear HTTP status codes and messages.
- Streamlit displays success and error messages for all major workflows.

## Future Improvements

- Add Alembic migrations for production-grade schema changes.
- Replace local hash embeddings with a hosted embedding model.
- Add password reset and email verification.
- Add audit logs for admin decisions.
- Add encrypted file storage for sensitive documents.
- Add unit and integration tests with pytest.
- Add role management for multiple admin levels.
- Add deployment files for Docker or cloud hosting.
