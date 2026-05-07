# API Reference

Base URL for local development: `http://127.0.0.1:8000`

Authenticated endpoints require:

```text
Authorization: Bearer <access_token>
```

## Auth

`POST /signup`

Creates a customer account and returns a JWT.

```json
{
  "name": "Demo Customer",
  "email": "demo.customer@example.com",
  "phone": "+1-555-0100",
  "password": "CustomerPass123!"
}
```

`POST /login`

Returns a JWT for a valid user.

```json
{
  "email": "admin@loanbot.local",
  "password": "AdminPass123!"
}
```

`GET /me`

Returns the current authenticated user.

## Loan Applications

`POST /loan-applications`

Creates an application for the authenticated customer.

```json
{
  "loan_type": "Personal Loan",
  "loan_amount": 15000,
  "monthly_income": 6000,
  "employment_type": "Salaried",
  "existing_emi": 450,
  "remarks": "Customer wants document guidance."
}
```

`POST /loan-applications/eligibility`

Checks estimated eligibility before submission.

```json
{
  "monthly_income": 6000,
  "existing_emi": 450,
  "loan_amount": 15000,
  "employment_type": "Salaried",
  "missing_documents": 0
}
```

`GET /loan-applications`

Lists applications for the authenticated customer.

`GET /loan-applications/{application_id}`

Returns one application. Customers can access their own applications; admins can access any application.

## Documents

`POST /loan-applications/{application_id}/documents`

Uploads local file bytes into `uploads/` and links the document to an application.

Send raw file bytes with headers:

```text
X-Filename: income-proof.pdf
X-Document-Type: income_proof
```

`GET /loan-applications/{application_id}/documents`

Lists documents for an application.

## Admin

`GET /admin/applications`

Lists all loan applications. Requires admin JWT.

`PATCH /admin/documents/{document_id}/verification`

Updates document verification status. Requires admin JWT.

```json
{
  "verification_status": "verified",
  "remarks": "Document is clear and matches the applicant details."
}
```

`PATCH /admin/applications/{application_id}/credit-decision`

Updates credit decision and records an admin review. Requires admin JWT.

```json
{
  "credit_decision": "manual_review_required",
  "application_status": "under_review",
  "risk_score": 0.34,
  "remarks": "Request latest bank statement before final decision."
}
```

## Chatbot

`POST /chatbot`

Sends an authenticated customer question through RAG and OpenRouter.

```json
{
  "message": "What documents are needed for a home loan?",
  "application_id": 1
}
```

## Utilities

`GET /health`

Returns backend status.

`POST /documents/index-samples`

Indexes sample knowledge files. Requires admin JWT.
