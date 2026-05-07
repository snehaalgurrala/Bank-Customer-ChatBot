# Architecture

The project separates user interface, API orchestration, storage, and retrieval logic.

## Runtime flow

1. Streamlit sends customer, loan, upload, and chat requests to FastAPI.
2. FastAPI stores structured records in SQLite through SQLAlchemy models.
3. Uploaded files are saved in the local `uploads` folder.
4. Supported documents are split by LangChain and indexed in ChromaDB.
5. Chat requests retrieve relevant ChromaDB chunks and pass them to OpenRouter with a banking-safe system prompt.

## Local data

- SQLite database: `database/chatbot.db`
- Uploaded files: `uploads/`
- Chroma persistence: `vectorstore/chroma/`
- Starter knowledge: `sample_data/`

## Production notes

- Replace local fake embeddings with a production embedding provider.
- Restrict CORS origins to approved frontend domains.
- Add authentication and authorization before handling real customer records.
- Encrypt sensitive files and never store regulated documents in this demo upload folder.
