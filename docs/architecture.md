# Architecture

The project separates user interface, API orchestration, storage, and retrieval logic.

## Runtime flow

1. Streamlit sends customer, loan, upload, and chat requests to FastAPI.
2. FastAPI stores structured records in SQLite through SQLAlchemy models.
3. Uploaded files are saved in the local `uploads` folder.
4. Supported documents are split by LangChain and indexed in ChromaDB.
5. Chat requests retrieve relevant ChromaDB chunks and pass them to OpenRouter with a banking-safe system prompt.
6. Database tools add user-specific context for application status, missing documents, eligibility, and credit decisions.

## Local data

- SQLite database: `database/chatbot.db`
- Uploaded files: `uploads/`
- Chroma persistence: `vectorstore/chroma/`
- Starter knowledge: `sample_data/`

## RAG Policy Corpus

Sample policy documents cover personal loan eligibility, required documents, credit decision rules, rejection reasons, document verification, and the loan approval workflow. Run `POST /documents/index-samples` as an admin or call `index_policy_documents()` from `utils.rag` to load, chunk, embed, and store the policy corpus in ChromaDB.

## Database tables

- `users`
- `loan_applications`
- `documents`
- `chatbot_logs`
- `admin_reviews`

Run `python -m database.init_db` to create tables and insert demo seed data. For an older local development database, run `python -m database.init_db --reset`.

## Production notes

- Replace local fake embeddings with a production embedding provider.
- Restrict CORS origins to approved frontend domains.
- Add authentication and authorization before handling real customer records.
- Encrypt sensitive files and never store regulated documents in this demo upload folder.
