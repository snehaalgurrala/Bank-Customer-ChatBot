# API Reference

Base URL for local development: `http://127.0.0.1:8000`

## Health

`GET /health`

Returns backend status and app name.

## Customers

`POST /customers`

Creates a customer or returns the existing customer for the submitted email.

```json
{
  "full_name": "Demo Customer",
  "email": "demo.customer@example.com",
  "phone": "+1-555-0100"
}
```

## Loan applications

`POST /loan-applications`

Creates a starter loan application for an existing customer.

`GET /loan-applications/{customer_id}`

Lists applications for a customer.

## Chat

`POST /chat`

Sends a customer question through the RAG pipeline and OpenRouter.

```json
{
  "message": "What documents are needed for a home loan?",
  "customer_id": 1
}
```

## Documents

`POST /documents/upload`

Uploads and indexes `.txt`, `.md`, or `.pdf` knowledge documents.

Send raw file bytes with headers:

```text
X-Filename: policy.md
X-Content-Type: text/markdown
```

`POST /documents/index-samples`

Indexes the files in `sample_data`.

`GET /documents`

Lists uploaded documents recorded in SQLite.
