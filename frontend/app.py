from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

API_URL = os.getenv("FRONTEND_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="Loan Assistance Chatbot", page_icon=":bank:", layout="wide")


def init_state() -> None:
    defaults = {
        "access_token": None,
        "user": None,
        "page": "Login",
        "chat_messages": [],
        "selected_application_id": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_state()


def auth_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = dict(extra or {})
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    return headers


def api_request(method: str, path: str, **kwargs: Any) -> Any:
    # Centralized API helper keeps JWT headers and error display consistent.
    headers = auth_headers(kwargs.pop("headers", None))
    response = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=60, **kwargs)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except ValueError:
            pass
        raise RuntimeError(str(detail)) from exc
    if not response.content:
        return None
    return response.json()


def signed_in() -> bool:
    return bool(st.session_state.access_token and st.session_state.user)


def is_admin() -> bool:
    return signed_in() and st.session_state.user.get("role") == "admin"


def set_session(data: dict[str, Any]) -> None:
    st.session_state.access_token = data["access_token"]
    st.session_state.user = data["user"]
    st.session_state.page = "Admin Dashboard" if data["user"]["role"] == "admin" else "Applicant Dashboard"


def logout() -> None:
    st.session_state.access_token = None
    st.session_state.user = None
    st.session_state.chat_messages = []
    st.session_state.selected_application_id = None
    st.session_state.page = "Login"


def money(value: float | int | None) -> str:
    return f"${value:,.2f}" if value is not None else "-"


def status_badge(value: str | None) -> str:
    return (value or "pending").replace("_", " ").title()


st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem;}
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 16px;
    }
    .section-note {
        color: #475569;
        font-size: 0.95rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def sidebar() -> None:
    with st.sidebar:
        st.title("LoanAssist")
        st.caption("AI Customer Loan Assistance")
        try:
            health = api_request("GET", "/health")
            st.success(f"API {health['status']}")
        except Exception as exc:
            st.error(f"API unavailable: {exc}")

        if signed_in():
            user = st.session_state.user
            st.divider()
            st.write(user["name"])
            st.caption(f"{user['email']} | {user['role']}")
            if st.button("Log out", use_container_width=True):
                logout()
                st.rerun()

        st.divider()
        if not signed_in():
            pages = ["Login", "Signup"]
        elif is_admin():
            pages = ["Admin Dashboard", "Admin Document Review", "Admin Credit Decision", "AI Chatbot"]
        else:
            pages = [
                "Applicant Dashboard",
                "Loan Application Form",
                "Document Upload",
                "Application Status",
                "AI Chatbot",
            ]

        current = st.session_state.page if st.session_state.page in pages else pages[0]
        st.session_state.page = st.radio("Navigation", pages, index=pages.index(current), label_visibility="collapsed")


def page_header(title: str, caption: str) -> None:
    st.title(title)
    st.caption(caption)


def login_page() -> None:
    page_header("Login", "Access your secure loan assistance workspace.")
    col_form, col_info = st.columns([1, 1])
    with col_form:
        with st.form("login_form"):
            email = st.text_input("Email", value="demo.customer@example.com")
            password = st.text_input("Password", value="CustomerPass123!", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True)
            if submitted:
                try:
                    data = api_request("POST", "/login", json={"email": email, "password": password})
                    set_session(data)
                    st.success("Login successful.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Login failed: {exc}")
    with col_info:
        st.subheader("Demo credentials")
        st.write("Customer: `demo.customer@example.com` / `CustomerPass123!`")
        st.write("Admin: `admin@loanbot.local` / `AdminPass123!`")


def signup_page() -> None:
    page_header("Signup", "Create a customer account to apply for a loan.")
    with st.form("signup_form"):
        name = st.text_input("Full name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            try:
                data = api_request(
                    "POST",
                    "/signup",
                    json={"name": name, "email": email, "phone": phone or None, "password": password},
                )
                set_session(data)
                st.success("Account created.")
                st.rerun()
            except Exception as exc:
                st.error(f"Signup failed: {exc}")


def fetch_my_applications() -> list[dict[str, Any]]:
    return api_request("GET", "/loan-applications")


def fetch_admin_applications() -> list[dict[str, Any]]:
    return api_request("GET", "/admin/applications")


def application_picker(applications: list[dict[str, Any]], key: str) -> int | None:
    if not applications:
        st.info("No applications found.")
        return None
    labels = {
        f"#{app['id']} - {app['loan_type']} - {status_badge(app['application_status'])}": app["id"]
        for app in applications
    }
    selected_label = st.selectbox("Application", list(labels.keys()), key=key)
    return labels[selected_label]


def admin_application_label(app: dict[str, Any]) -> str:
    applicant = app.get("user", {})
    applicant_name = applicant.get("name", f"User {app['user_id']}")
    return f"#{app['id']} - {applicant_name} - {app['loan_type']} - {status_badge(app['application_status'])}"


def filtered_admin_applications(applications: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    statuses = sorted({app["application_status"] for app in applications})
    selected_status = st.selectbox("Filter by status", ["All"] + statuses, key=key)
    if selected_status == "All":
        return applications
    return [app for app in applications if app["application_status"] == selected_status]


def admin_application_selector(applications: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    if not applications:
        st.info("No applications match the selected filter.")
        return None
    labels = {admin_application_label(app): app for app in applications}
    label = st.selectbox("Select application", list(labels.keys()), key=key)
    return labels[label]


def render_applicant_details(application: dict[str, Any]) -> None:
    applicant = application.get("user", {})
    st.subheader("Applicant Details")
    col1, col2, col3 = st.columns(3)
    col1.metric("Applicant", applicant.get("name", "-"))
    col2.metric("Email", applicant.get("email", "-"))
    col3.metric("Phone", applicant.get("phone") or "-")

    st.subheader("Loan Details")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Requested", money(application.get("loan_amount")))
    col2.metric("Approved", money(application.get("approved_amount")))
    col3.metric("Monthly income", money(application.get("monthly_income")))
    col4.metric("Risk score", application.get("risk_score") if application.get("risk_score") is not None else "-")
    st.caption(application.get("remarks") or "No remarks added yet.")


def render_document_review(application_id: int) -> None:
    st.subheader("Uploaded Documents")
    try:
        documents = api_request("GET", f"/loan-applications/{application_id}/documents")
    except Exception as exc:
        st.error(f"Could not load documents: {exc}")
        return
    if not documents:
        st.info("No documents uploaded for this application.")
        return

    st.dataframe(documents, use_container_width=True, hide_index=True)
    document_options = {
        f"#{doc['id']} - {doc['document_type']} - {status_badge(doc['verification_status'])}": doc
        for doc in documents
    }
    selected_doc_label = st.selectbox("Document to review", list(document_options.keys()), key=f"doc_select_{application_id}")
    selected_doc = document_options[selected_doc_label]

    with st.form(f"document_review_form_{selected_doc['id']}"):
        col1, col2 = st.columns([1, 2])
        with col1:
            verification_status = st.selectbox(
                "Verification status",
                ["verified", "rejected", "needs_resubmission", "pending"],
                index=["verified", "rejected", "needs_resubmission", "pending"].index(selected_doc["verification_status"])
                if selected_doc["verification_status"] in ["verified", "rejected", "needs_resubmission", "pending"]
                else 3,
            )
        with col2:
            remarks = st.text_area("Document remarks", value=selected_doc.get("remarks") or "")
        submitted = st.form_submit_button("Update document review", use_container_width=True)
        if submitted:
            try:
                document = api_request(
                    "PATCH",
                    f"/admin/documents/{selected_doc['id']}/verification",
                    json={"verification_status": verification_status, "remarks": remarks or None},
                )
                st.success(f"Document #{document['id']} marked {document['verification_status']}.")
            except Exception as exc:
                st.error(f"Document update failed: {exc}")


def render_credit_decision(application: dict[str, Any]) -> None:
    st.subheader("Credit Decision")
    with st.form(f"credit_decision_form_{application['id']}"):
        col1, col2, col3 = st.columns(3)
        with col1:
            credit_decision = st.selectbox(
                "Credit decision",
                ["approved", "rejected", "manual_review_required", "needs_documents", "pending"],
                index=["approved", "rejected", "manual_review_required", "needs_documents", "pending"].index(
                    application.get("credit_decision") or "pending"
                )
                if (application.get("credit_decision") or "pending")
                in ["approved", "rejected", "manual_review_required", "needs_documents", "pending"]
                else 4,
            )
        with col2:
            application_status = st.selectbox(
                "Application status",
                ["approved", "rejected", "pending", "submitted", "under_review", "needs_documents"],
                index=["approved", "rejected", "pending", "submitted", "under_review", "needs_documents"].index(
                    application.get("application_status") or "pending"
                )
                if (application.get("application_status") or "pending")
                in ["approved", "rejected", "pending", "submitted", "under_review", "needs_documents"]
                else 2,
            )
        with col3:
            approved_amount = st.number_input(
                "Approved amount",
                min_value=0.0,
                value=float(application.get("approved_amount") or application.get("loan_amount") or 0),
                step=500.0,
            )
        risk_score = st.slider("Risk score", 0.0, 1.0, float(application.get("risk_score") or 0.5), 0.01)
        remarks = st.text_area("Credit remarks", value=application.get("remarks") or "")
        submitted = st.form_submit_button("Save credit decision", use_container_width=True)
        if submitted:
            try:
                updated = api_request(
                    "PATCH",
                    f"/admin/applications/{application['id']}/credit-decision",
                    json={
                        "credit_decision": credit_decision,
                        "application_status": application_status,
                        "approved_amount": approved_amount,
                        "risk_score": risk_score,
                        "remarks": remarks or None,
                    },
                )
                st.success(f"Application #{updated['id']} updated.")
            except Exception as exc:
                st.error(f"Credit decision update failed: {exc}")


def render_ai_credit_summary(application: dict[str, Any]) -> None:
    st.subheader("AI Credit Summary")
    if st.button("Generate AI credit summary", use_container_width=True):
        prompt = (
            "Generate a concise admin credit summary for this application. "
            "Include application status, document readiness, eligibility, credit decision, risk score, "
            "pending reasons, and recommended next action."
        )
        try:
            data = api_request("POST", "/chatbot", json={"message": prompt, "application_id": application["id"]})
            st.success("AI summary generated.")
            st.markdown(data["answer"])
        except Exception as exc:
            st.error(f"AI summary failed: {exc}")


def admin_review_workspace(scope: str) -> None:
    # One admin workspace powers dashboard, document review, and credit decision pages.
    try:
        applications = fetch_admin_applications()
    except Exception as exc:
        st.error(f"Could not load admin applications: {exc}")
        return
    filtered = filtered_admin_applications(applications, f"{scope}_status_filter")
    selected = admin_application_selector(filtered, f"{scope}_application_select")
    if not selected:
        return

    st.divider()
    tabs = st.tabs(["Applicant", "Documents", "Credit Decision", "AI Summary"])
    with tabs[0]:
        render_applicant_details(selected)
    with tabs[1]:
        render_document_review(selected["id"])
    with tabs[2]:
        render_credit_decision(selected)
    with tabs[3]:
        render_ai_credit_summary(selected)


def applicant_dashboard_page() -> None:
    page_header("Applicant Dashboard", "Review your loan activity and continue your application.")
    try:
        applications = fetch_my_applications()
    except Exception as exc:
        st.error(f"Could not load applications: {exc}")
        return

    total_requested = sum(app["loan_amount"] for app in applications)
    active_count = sum(1 for app in applications if app["application_status"] not in {"approved", "rejected"})
    col1, col2, col3 = st.columns(3)
    col1.metric("Applications", len(applications))
    col2.metric("Active reviews", active_count)
    col3.metric("Requested amount", money(total_requested))

    st.subheader("Recent applications")
    if applications:
        st.dataframe(applications, use_container_width=True, hide_index=True)
    else:
        st.info("Start with the Loan Application Form page.")


def loan_application_form_page() -> None:
    page_header("Loan Application Form", "Submit income, employment, and repayment details.")
    with st.form("loan_application_form"):
        col1, col2 = st.columns(2)
        with col1:
            loan_type = st.selectbox("Loan type", ["Personal Loan", "Home Loan", "Auto Loan", "Debt Consolidation"])
            loan_amount = st.number_input("Loan amount", min_value=1000.0, value=15000.0, step=500.0)
            monthly_income = st.number_input("Monthly income", min_value=1000.0, value=6000.0, step=500.0)
        with col2:
            employment_type = st.selectbox("Employment type", ["Salaried", "Self-employed", "Contract", "Retired"])
            existing_emi = st.number_input("Existing EMI", min_value=0.0, value=450.0, step=50.0)
            remarks = st.text_area("Remarks", value="Interested in document and eligibility guidance.")
        submitted = st.form_submit_button("Submit application", use_container_width=True)
        if submitted:
            try:
                application = api_request(
                    "POST",
                    "/loan-applications",
                    json={
                        "loan_type": loan_type,
                        "loan_amount": loan_amount,
                        "monthly_income": monthly_income,
                        "employment_type": employment_type,
                        "existing_emi": existing_emi,
                        "remarks": remarks,
                    },
                )
                st.session_state.selected_application_id = application["id"]
                st.success(f"Application #{application['id']} submitted successfully.")
            except Exception as exc:
                st.error(f"Application submission failed: {exc}")


def document_upload_page() -> None:
    page_header("Document Upload", "Upload income, identity, and loan supporting files.")
    try:
        applications = fetch_my_applications()
    except Exception as exc:
        st.error(f"Could not load applications: {exc}")
        return
    application_id = application_picker(applications, "upload_application")
    if not application_id:
        return

    document_type = st.selectbox("Document type", ["identity_proof", "income_proof", "bank_statement", "address_proof", "other"])
    uploaded = st.file_uploader("Upload document", type=["txt", "md", "pdf", "png", "jpg", "jpeg"])
    if uploaded and st.button("Upload document", use_container_width=True):
        try:
            document = api_request(
                "POST",
                f"/loan-applications/{application_id}/documents",
                headers={"X-Filename": uploaded.name, "X-Document-Type": document_type},
                data=uploaded.getvalue(),
            )
            st.success(f"Uploaded document #{document['id']} for application #{application_id}.")
        except Exception as exc:
            st.error(f"Upload failed: {exc}")


def application_status_page() -> None:
    page_header("Application Status", "Track decisions, review status, and document verification.")
    try:
        applications = fetch_my_applications()
    except Exception as exc:
        st.error(f"Could not load applications: {exc}")
        return
    application_id = application_picker(applications, "status_application")
    if not application_id:
        return

    try:
        application = api_request("GET", f"/loan-applications/{application_id}")
        documents = api_request("GET", f"/loan-applications/{application_id}/documents")
    except Exception as exc:
        st.error(f"Could not load status: {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Application status", status_badge(application["application_status"]))
    col2.metric("Credit decision", status_badge(application["credit_decision"]))
    col3.metric("Risk score", application["risk_score"] if application["risk_score"] is not None else "-")

    st.subheader("Application details")
    st.json(application)
    st.subheader("Documents")
    if documents:
        st.dataframe(documents, use_container_width=True, hide_index=True)
    else:
        st.info("No documents uploaded for this application.")


def chatbot_page() -> None:
    page_header("AI Chatbot", "Ask questions about loan eligibility, documents, and next steps.")
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask a loan question")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Reviewing policy knowledge..."):
                try:
                    data = api_request("POST", "/chatbot", json={"message": prompt})
                    st.markdown(data["answer"])
                    if data.get("sources"):
                        with st.expander("Sources"):
                            for source in data["sources"]:
                                page = f" page {source['page']}" if source.get("page") else ""
                                st.write(f"{source['source']}{page}")
                    st.session_state.chat_messages.append({"role": "assistant", "content": data["answer"]})
                except Exception as exc:
                    st.error(f"Chatbot request failed: {exc}")


def admin_dashboard_page() -> None:
    page_header("Admin Dashboard", "Review applications, documents, decisions, and AI credit summaries.")
    try:
        applications = fetch_admin_applications()
    except Exception as exc:
        st.error(f"Could not load admin applications: {exc}")
        return
    pending = sum(1 for app in applications if app["application_status"] in {"submitted", "under_review"})
    approved = sum(1 for app in applications if app["credit_decision"] == "approved")
    total_requested = sum(app["loan_amount"] for app in applications)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total applications", len(applications))
    col2.metric("Pending review", pending)
    col3.metric("Portfolio requested", money(total_requested))

    if st.button("Index sample knowledge", use_container_width=True):
        try:
            result = api_request("POST", "/documents/index-samples")
            st.success(f"Indexed {result['indexed_chunks']} chunks.")
        except Exception as exc:
            st.error(f"Indexing failed: {exc}")

    admin_review_workspace("admin_dashboard")


def admin_document_review_page() -> None:
    page_header("Admin Document Review", "Verify documents submitted for loan applications.")
    admin_review_workspace("admin_documents")


def admin_credit_decision_page() -> None:
    page_header("Admin Credit Decision", "Record approval, rejection, or manual review outcomes.")
    admin_review_workspace("admin_credit")


sidebar()

pages = {
    "Login": login_page,
    "Signup": signup_page,
    "Applicant Dashboard": applicant_dashboard_page,
    "Loan Application Form": loan_application_form_page,
    "Document Upload": document_upload_page,
    "Application Status": application_status_page,
    "AI Chatbot": chatbot_page,
    "Admin Dashboard": admin_dashboard_page,
    "Admin Document Review": admin_document_review_page,
    "Admin Credit Decision": admin_credit_decision_page,
}

pages[st.session_state.page]()
