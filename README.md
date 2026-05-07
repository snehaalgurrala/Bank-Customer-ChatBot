# AI Customer Loan Assistance Chatbot

A complete starter Python project for a bank loan assistance chatbot using Streamlit, FastAPI, SQLite, SQLAlchemy, OpenRouter, ChromaDB, LangChain, and local file uploads.

## Project structure

```text
backend/       FastAPI routes and request/response schemas
frontend/      Streamlit customer-facing interface
database/      SQLAlchemy models, engine, and seed data
uploads/       Local uploaded document storage
vectorstore/   ChromaDB persistence folder
sample_data/   Starter loan FAQ and document checklist
docs/          Architecture and API notes
utils/         Shared config, OpenRouter client, and RAG helpers
```

## Setup

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

4. Edit `.env` and set `OPENROUTER_API_KEY`.

5. Initialize the SQLite database and seed demo data.

```powershell
python -m database.init_db
```

For an existing local development database from an older schema, recreate the tables:

```powershell
python -m database.init_db --reset
```

Seeded local credentials:

```text
Admin: admin@loanbot.local / AdminPass123!
Customer: demo.customer@example.com / CustomerPass123!
```

## Run the backend

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open API docs at `http://127.0.0.1:8000/docs`.

## Run the frontend

In a second terminal:

```powershell
streamlit run frontend/app.py
```

## First use

1. Click `Index sample knowledge` in the Streamlit sidebar.
2. Create or load the demo customer.
3. Ask a loan question in the chat tab.
4. Upload additional `.txt`, `.md`, or `.pdf` knowledge documents from the Documents tab.

The RAG corpus in `sample_data/` includes policy notes for eligibility, required documents, credit rules, rejection reasons, document verification, and approval workflow.

## Notes

The starter RAG pipeline uses LangChain with ChromaDB and local deterministic fake embeddings so the project runs without a second AI provider. For production, replace `FakeEmbeddings` in `utils/rag.py` with a real embedding model and add authentication, encrypted storage, audit logging, and compliance review.
