# Architecture

The project separates UI, API, persistence, local file storage, RAG retrieval, and AI orchestration.

## Text Diagram

```text
Streamlit Frontend
  |-- Login / Signup
  |-- Applicant Dashboard
  |-- Document Upload
  |-- Admin Dashboard
  `-- AI Chatbot
          |
          | HTTP requests + JWT bearer token
          v
FastAPI Backend
  |-- Auth and role checks
  |-- Loan application APIs
  |-- Document upload APIs
  |-- Admin decision APIs
  `-- Chatbot endpoint
          |
          | SQLAlchemy
          v
SQLite Database
  |-- users
  |-- loan_applications
  |-- documents
  |-- chatbot_logs
  `-- admin_reviews
          |
          v
Agentic AI Service
  |-- Application status tool
  |-- Missing document checker
  |-- Eligibility calculator
  |-- Credit decision explanation
  `-- RAG policy answer tool
          |
          | LangChain loaders, chunking, local embeddings
          v
ChromaDB Vectorstore
          |
          | retrieved context
          v
OpenRouter LLM
```

## Runtime Flow

1. Streamlit sends customer, loan, document, admin, and chat requests to FastAPI.
2. FastAPI validates requests with Pydantic and authorizes users with JWT.
3. SQLAlchemy reads and writes structured records in SQLite.
4. Uploaded files are stored in `uploads/`.
5. Text, Markdown, and PDF documents can be chunked and indexed into ChromaDB.
6. The chatbot route chooses one tool based on the user question.
7. Database tools return application-specific context when needed.
8. The RAG policy tool retrieves policy chunks from ChromaDB.
9. OpenRouter receives the selected tool result, RAG context, and conversation history.
10. Every chatbot exchange is stored in `chatbot_logs`.

## Local Data

- SQLite database: `database/chatbot.db`
- Uploaded files: `uploads/`
- Chroma persistence: `vectorstore/chroma/`
- RAG policy files: `sample_data/`

## Database Tables

- `users`
- `loan_applications`
- `documents`
- `chatbot_logs`
- `admin_reviews`

Run:

```powershell
python -m database.init_db
```

Reset an older local schema:

```powershell
python -m database.init_db --reset
```

## Production Notes

- Replace local hash embeddings with a production embedding provider.
- Restrict CORS origins to approved frontend domains.
- Store documents in encrypted object storage.
- Add Alembic migrations.
- Add audit logging for all admin actions.
- Add automated tests and CI.
