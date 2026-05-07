from __future__ import annotations

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("FRONTEND_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="Loan Assistance Chatbot", page_icon=":bank:", layout="wide")


def api_post(path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.get("access_token"):
        headers = {"Authorization": f"Bearer {st.session_state.access_token}", **headers}
    response = requests.post(f"{API_URL}{path}", headers=headers, timeout=60, **kwargs)
    response.raise_for_status()
    return response.json()


def api_get(path: str):
    headers = {}
    if st.session_state.get("access_token"):
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    response = requests.get(f"{API_URL}{path}", headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def ensure_state() -> None:
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("access_token", None)
    st.session_state.setdefault("application_id", None)
    st.session_state.setdefault("messages", [])


ensure_state()

st.title("AI Customer Loan Assistance Chatbot")
st.caption("Ask loan questions, submit a starter application, and upload knowledge documents for RAG answers.")

with st.sidebar:
    st.header("Backend")
    st.write(API_URL)
    try:
        health = api_get("/health")
        st.success(f"{health['status']} - {health['app_name']}")
    except requests.RequestException as exc:
        st.error(f"Backend unavailable: {exc}")

    with st.form("login_form"):
        email = st.text_input("Email", value="demo.customer@example.com")
        password = st.text_input("Password", value="CustomerPass123!", type="password")
        if st.form_submit_button("Log in"):
            try:
                data = api_post("/login", json={"email": email, "password": password})
                st.session_state.access_token = data["access_token"]
                st.session_state.user_id = data["user"]["id"]
                st.success(f"Signed in as {data['user']['role']}")
            except requests.RequestException as exc:
                st.error(f"Login failed: {exc}")

    if st.button("Index sample knowledge"):
        try:
            result = api_post("/documents/index-samples")
            st.success(f"Indexed {result['indexed_chunks']} chunks.")
        except requests.RequestException as exc:
            st.error(f"Indexing failed: {exc}")

tab_chat, tab_profile, tab_uploads = st.tabs(["Chat", "Customer & Loan", "Documents"])

with tab_chat:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask about eligibility, documents, loan types, or application steps")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Checking the loan knowledge base..."):
                try:
                    data = api_post("/chatbot", json={"message": prompt})
                    answer = data["answer"]
                    st.markdown(answer)
                    if data.get("sources"):
                        with st.expander("Sources"):
                            for source in data["sources"]:
                                page = f" page {source['page']}" if source.get("page") else ""
                                st.write(f"{source['source']}{page}")
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except requests.RequestException as exc:
                    st.error(f"Chat request failed: {exc}")

with tab_profile:
    col_customer, col_loan = st.columns(2)

    with col_customer:
        st.subheader("Customer")
        with st.form("customer_form"):
            full_name = st.text_input("Full name", value="Demo Customer")
            email = st.text_input("Email", value="demo.customer@example.com")
            phone = st.text_input("Phone", value="+1-555-0100")
            submitted = st.form_submit_button("Create or load customer")
            if submitted:
                try:
                    data = api_post(
                        "/signup",
                        json={
                            "name": full_name,
                            "email": email,
                            "phone": phone or None,
                            "password": "CustomerPass123!",
                        },
                    )
                    st.session_state.access_token = data["access_token"]
                    st.session_state.user_id = data["user"]["id"]
                    st.success(f"Using user ID {data['user']['id']}")
                except requests.RequestException as exc:
                    st.error(f"Customer save failed: {exc}")

    with col_loan:
        st.subheader("Starter loan application")
        with st.form("loan_form"):
            loan_type = st.selectbox("Loan type", ["Personal Loan", "Home Loan", "Auto Loan", "Debt Consolidation"])
            amount = st.number_input("Requested amount", min_value=1000.0, value=15000.0, step=500.0)
            monthly_income = st.number_input("Monthly income", min_value=1000.0, value=6000.0, step=500.0)
            employment_type = st.selectbox("Employment type", ["Salaried", "Self-employed", "Contract", "Retired"])
            existing_emi = st.number_input("Existing EMI", min_value=0.0, value=450.0, step=50.0)
            notes = st.text_area("Notes", value="Interested in monthly payment estimates and document requirements.")
            submitted = st.form_submit_button("Submit application")
            if submitted:
                if not st.session_state.user_id:
                    st.warning("Create or load a customer first.")
                else:
                    try:
                        application = api_post(
                            "/loan-applications",
                            json={
                                "loan_type": loan_type,
                                "loan_amount": amount,
                                "monthly_income": monthly_income,
                                "employment_type": employment_type,
                                "existing_emi": existing_emi,
                                "remarks": notes,
                            },
                        )
                        st.session_state.application_id = application["id"]
                        st.success(f"Application #{application['id']} submitted.")
                    except requests.RequestException as exc:
                        st.error(f"Application submit failed: {exc}")

with tab_uploads:
    st.subheader("Knowledge documents")
    app_id = st.number_input("Application ID", min_value=1, value=st.session_state.application_id or 1, step=1)
    uploaded = st.file_uploader("Upload .txt, .md, or .pdf", type=["txt", "md", "pdf"])
    if uploaded and st.button("Upload and index"):
        try:
            headers = {"X-Filename": uploaded.name, "X-Document-Type": "supporting_document"}
            document = api_post(f"/loan-applications/{app_id}/documents", data=uploaded.getvalue(), headers=headers)
            st.success(f"Stored {document['document_type']} at {document['file_path']}.")
        except requests.RequestException as exc:
            st.error(f"Upload failed: {exc}")

    try:
        documents = api_get(f"/loan-applications/{app_id}/documents")
        if documents:
            st.dataframe(documents, use_container_width=True)
        else:
            st.info("No uploaded documents yet. Sample data can be indexed from the sidebar.")
    except requests.RequestException:
        st.info("Start the backend to view indexed documents.")
