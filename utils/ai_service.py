from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from database.models import ChatbotLog, User
from utils.chatbot_tools import (
    calculate_application_eligibility,
    check_application_status,
    check_missing_documents,
    get_credit_decision,
)
from utils.openrouter_client import OpenRouterError, chat_completion
from utils.rag import retrieve_context


def _selected_tools(message: str) -> list[str]:
    text = message.lower()
    tools: list[str] = []
    if any(word in text for word in ["status", "pending", "progress", "stage", "after document"]):
        tools.append("check_application_status")
    if any(word in text for word in ["missing", "documents required", "required documents", "what documents", "document"]):
        tools.append("check_missing_documents")
    if any(word in text for word in ["eligible", "eligibility", "afford", "qualify", "loan amount"]):
        tools.append("calculate_eligibility")
    if any(word in text for word in ["decision", "approved", "rejected", "credit"]):
        tools.append("get_credit_decision")
    if not tools:
        tools = ["check_application_status"]
    return list(dict.fromkeys(tools))


def _run_tools(db: Session, user: User, message: str, application_id: int | None) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for tool_name in _selected_tools(message):
        if tool_name == "check_application_status":
            results[tool_name] = check_application_status(db, user, application_id)
        elif tool_name == "check_missing_documents":
            results[tool_name] = check_missing_documents(db, user, application_id)
        elif tool_name == "calculate_eligibility":
            results[tool_name] = calculate_application_eligibility(db, user, application_id)
        elif tool_name == "get_credit_decision":
            results[tool_name] = get_credit_decision(db, user, application_id)
    return results


def _history(db: Session, user: User) -> list[dict[str, str]]:
    rows = (
        db.query(ChatbotLog)
        .filter(ChatbotLog.user_id == user.id)
        .order_by(ChatbotLog.timestamp.desc())
        .limit(4)
        .all()
    )
    conversation: list[dict[str, str]] = []
    for row in reversed(rows):
        conversation.append({"role": "user", "content": row.message})
        conversation.append({"role": "assistant", "content": row.bot_response})
    return conversation


def _local_answer(message: str, tool_results: dict[str, Any]) -> str:
    if "check_missing_documents" in tool_results:
        result = tool_results["check_missing_documents"]
        if result.get("found") and result.get("missing_documents"):
            missing = ", ".join(item["description"] for item in result["missing_documents"])
            return f"You still need to submit: {missing}. Upload them from the Document Upload page."
        if result.get("found"):
            return "All required document types have been uploaded. The bank team still needs to complete verification if any document is pending."
    if "calculate_eligibility" in tool_results:
        result = tool_results["calculate_eligibility"]
        if result.get("found"):
            return (
                f"Your estimated eligible amount is {result['eligible_amount']}. "
                f"Risk level is {result['risk_level']} with a score of {result['risk_score']}. "
                f"{result['recommendation']}"
            )
    if "get_credit_decision" in tool_results:
        result = tool_results["get_credit_decision"]
        if result.get("found"):
            return f"Your current credit decision is {result['credit_decision']}. Status: {result['application_status']}. {result.get('remarks') or ''}".strip()
    if "check_application_status" in tool_results:
        result = tool_results["check_application_status"]
        if result.get("found"):
            return f"Application #{result['application_id']} is currently {result['application_status']}. Credit decision: {result.get('credit_decision') or 'pending'}."
    return "I could not find an application yet. Please submit a loan application first, then I can check status, documents, eligibility, and credit decision."


def answer_user_question(db: Session, user: User, message: str, application_id: int | None = None) -> tuple[str, list[dict[str, str]]]:
    tool_results = _run_tools(db, user, message, application_id)
    rag_context, sources = retrieve_context(message)
    tool_context = json.dumps(tool_results, indent=2, default=str)
    context = (
        "Database tool results are authoritative for this user. "
        "Use them when answering status, missing document, eligibility, pending, or credit decision questions.\n\n"
        f"Tool results:\n{tool_context}\n\nKnowledge base context:\n{rag_context}"
    )
    try:
        answer = chat_completion(message, context=context, conversation=_history(db, user))
    except OpenRouterError:
        answer = _local_answer(message, tool_results)
    if "OpenRouter is not configured yet" in answer:
        answer = _local_answer(message, tool_results)

    db.add(ChatbotLog(user_id=user.id, message=message, bot_response=answer))
    db.commit()
    return answer, sources
