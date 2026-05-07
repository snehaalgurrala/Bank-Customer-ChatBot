from __future__ import annotations

import requests

from utils.config import get_settings


SYSTEM_PROMPT = """You are a careful customer loan assistance chatbot for a bank.
Help customers understand loan products, required documents, eligibility factors, and application next steps.
Do not guarantee approval, invent rates, or request full sensitive secrets such as passwords.
When the answer depends on bank policy, say what information is available and recommend contacting a loan officer."""


class OpenRouterError(RuntimeError):
    """Raised when the OpenRouter API call fails."""


def build_messages(question: str, context: str = "", conversation: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    context_block = context.strip() or "No retrieved knowledge base context was found."
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"Use this retrieved knowledge base context when relevant:\n\n{context_block}",
        },
    ]
    if conversation:
        messages.extend(conversation[-8:])
    messages.append({"role": "user", "content": question})
    return messages


def chat_completion(question: str, context: str = "", conversation: list[dict[str, str]] | None = None) -> str:
    settings = get_settings()
    if not settings.openrouter_api_key or settings.openrouter_api_key.startswith("replace-"):
        return (
            "OpenRouter is not configured yet. Add OPENROUTER_API_KEY to your .env file, "
            "then restart the backend. Based on the local knowledge base, I can still help explain "
            "loan documents, eligibility factors, and next steps."
        )

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_app_name,
    }
    payload = {
        "model": settings.openrouter_model,
        "messages": build_messages(question, context, conversation),
        "temperature": 0.2,
        "max_tokens": 700,
    }
    response = requests.post(settings.openrouter_base_url, headers=headers, json=payload, timeout=45)
    if response.status_code >= 400:
        raise OpenRouterError(f"OpenRouter returned {response.status_code}: {response.text[:500]}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError("OpenRouter response did not include a usable assistant message.") from exc
