from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
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


class ChatbotTool(str, Enum):
    RAG_POLICY = "rag_policy_answer"
    APPLICATION_STATUS = "check_application_status"
    MISSING_DOCUMENTS = "check_missing_documents"
    ELIGIBILITY = "calculate_eligibility"
    CREDIT_DECISION = "get_credit_decision"


@dataclass(frozen=True)
class ToolRoute:
    tool: ChatbotTool
    reason: str
    needs_rag: bool = False


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _extract_requested_amount(message: str) -> float | None:
    text = message.lower().replace(",", "")
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs)", text)
    if lakh_match:
        return float(lakh_match.group(1)) * 100000
    crore_match = re.search(r"(\d+(?:\.\d+)?)\s*(crore|crores)", text)
    if crore_match:
        return float(crore_match.group(1)) * 10000000
    amount_match = re.search(r"(?:rs\.?|inr|₹|\$)?\s*(\d{4,})", text)
    if amount_match:
        return float(amount_match.group(1))
    return None


def route_tool(message: str) -> ToolRoute:
    text = f" {message.lower()} "

    if _contains_any(text, [" my loan status", " application status", " status of my", " track my", " progress "]):
        return ToolRoute(ChatbotTool.APPLICATION_STATUS, "User asked for application status.")

    if _contains_any(text, [" missing document", " documents missing", " which document", " what document is missing"]):
        return ToolRoute(ChatbotTool.MISSING_DOCUMENTS, "User asked which submitted/required documents are missing.")

    if _contains_any(text, [" am i eligible", " eligible for", " eligibility", " can i get", " qualify for", " afford "]):
        return ToolRoute(ChatbotTool.ELIGIBILITY, "User asked for loan eligibility or eligible amount.")

    if _contains_any(text, [" credit decision", " approved", " rejected", " approval decision", " why rejected"]):
        return ToolRoute(ChatbotTool.CREDIT_DECISION, "User asked about the credit decision.")

    if _contains_any(
        text,
        [
            "documents are required",
            "documents required",
            "required documents",
            "what documents",
            "document verification process",
            "approval workflow",
            "what happens after",
            "rejection reasons",
            "policy",
            "rules",
        ],
    ):
        return ToolRoute(ChatbotTool.RAG_POLICY, "User asked a general loan policy question.", needs_rag=True)

    return ToolRoute(ChatbotTool.RAG_POLICY, "Default to policy knowledge retrieval for general questions.", needs_rag=True)


def _run_selected_tool(
    db: Session,
    user: User,
    route: ToolRoute,
    message: str,
    application_id: int | None,
) -> dict[str, Any]:
    if route.tool == ChatbotTool.APPLICATION_STATUS:
        return {route.tool.value: check_application_status(db, user, application_id)}
    if route.tool == ChatbotTool.MISSING_DOCUMENTS:
        return {route.tool.value: check_missing_documents(db, user, application_id)}
    if route.tool == ChatbotTool.ELIGIBILITY:
        return {
            route.tool.value: calculate_application_eligibility(
                db,
                user,
                application_id,
                requested_loan_amount=_extract_requested_amount(message),
            )
        }
    if route.tool == ChatbotTool.CREDIT_DECISION:
        return {route.tool.value: get_credit_decision(db, user, application_id)}
    return {}


def _rag_query_for_route(message: str, route: ToolRoute) -> str:
    text = message.lower()
    if route.tool != ChatbotTool.RAG_POLICY:
        return message
    if "document" in text and "verification" not in text:
        return "required documents identity proof income proof bank statement additional documents"
    if "verification" in text or "after document" in text:
        return "document verification process after verification credit decision"
    if "rejection" in text or "rejected" in text:
        return "loan rejection reasons affordability missing documents identity verification"
    if "workflow" in text or "approval" in text:
        return "loan approval workflow application submitted documents verified credit decision"
    if "eligibility" in text:
        return "personal loan eligibility disposable income EMI capacity employment type"
    return message


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


def _rag_fallback(rag_context: str) -> str | None:
    if not rag_context.strip():
        return None
    snippets: list[str] = []
    for block in rag_context.split("\n\n---\n\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip() and not line.startswith("Source:")]
        if lines:
            snippets.append(" ".join(lines)[:360])
    if not snippets:
        return None
    return "Based on the loan policy knowledge base: " + " ".join(snippets[:2])


def _local_answer(route: ToolRoute, tool_results: dict[str, Any], rag_context: str) -> str:
    if route.tool == ChatbotTool.RAG_POLICY:
        return _rag_fallback(rag_context) or "I could not find relevant policy context. Please ask about eligibility, required documents, credit decisions, rejection reasons, or workflow."

    result = tool_results.get(route.tool.value, {})
    if not result.get("found", True):
        return result.get("message", "No matching loan application was found.")

    if route.tool == ChatbotTool.APPLICATION_STATUS:
        return f"Application #{result['application_id']} is currently {result['application_status']}. Credit decision: {result.get('credit_decision') or 'pending'}."

    if route.tool == ChatbotTool.MISSING_DOCUMENTS:
        missing_docs = result.get("missing_documents", [])
        if missing_docs:
            missing = ", ".join(item["description"] for item in missing_docs)
            return f"You still need to submit: {missing}. Upload them from the Document Upload page."
        return "All required document types have been uploaded. Any pending verification will be completed by the admin review team."

    if route.tool == ChatbotTool.ELIGIBILITY:
        return (
            f"Your estimated eligible amount is {result['eligible_amount']}. "
            f"Risk level is {result['risk_level']} with a score of {result['risk_score']}. "
            f"{result['recommendation']}"
        )

    if route.tool == ChatbotTool.CREDIT_DECISION:
        return f"Your current credit decision is {result['credit_decision']}. Status: {result['application_status']}. {result.get('remarks') or ''}".strip()

    return "I could not determine the right action for that question."


def answer_user_question(db: Session, user: User, message: str, application_id: int | None = None) -> tuple[str, list[dict[str, str]]]:
    route = route_tool(message)
    tool_results = _run_selected_tool(db, user, route, message, application_id)
    rag_context, sources = retrieve_context(_rag_query_for_route(message, route))

    context = (
        "You are an agentic loan chatbot. Use exactly the selected tool result when it exists; "
        "use retrieved policy context for policy questions. Do not invent application data.\n\n"
        f"Selected tool: {route.tool.value}\n"
        f"Routing reason: {route.reason}\n\n"
        f"Tool results:\n{json.dumps(tool_results, indent=2, default=str)}\n\n"
        f"Retrieved policy context:\n{rag_context}"
    )

    try:
        answer = chat_completion(message, context=context, conversation=_history(db, user))
    except OpenRouterError:
        answer = _local_answer(route, tool_results, rag_context)
    if "OpenRouter is not configured yet" in answer:
        answer = _local_answer(route, tool_results, rag_context)

    db.add(ChatbotLog(user_id=user.id, message=message, bot_response=answer))
    db.commit()
    return answer, sources
