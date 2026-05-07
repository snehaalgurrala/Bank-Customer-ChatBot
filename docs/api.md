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
  "name": "Demo Customer",
  "email": "demo.customer@example.com",
  "phone": "+1-555-0100",
  "password_hash": "pbkdf2:demo-password-hash",
  "role": "customer"
}
```

`POST /users` accepts the same payload.

## Loan applications

`POST /loan-applications`

Creates a starter loan application for an existing user.

```json
{
  "user_id": 1,
  "loan_type": "Personal Loan",
  "loan_amount": 15000,
  "monthly_income": 6000,
  "employment_type": "Salaried",
  "existing_emi": 450,
  "remarks": "Customer wants document guidance."
}
```

`GET /loan-applications/{user_id}`

Lists applications for a user.

## Chat

`POST /chat`

Sends a customer question through the RAG pipeline and OpenRouter.

```json
{
  "message": "What documents are needed for a home loan?",
  "user_id": 1
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

## Admin reviews

`GET /admin-reviews`

Lists seeded and created admin review records.
