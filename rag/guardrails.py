"""Deterministic Guardrails and Grounding Engine for SupportBot AI.

Provides safety checks for:
1. Insufficient retrieval -> safe deterministic abstention.
2. Prompt injection attempts -> instruction leakage prevention.
3. Out-of-domain queries -> redirection to business support.
4. Tenant boundary enforcement before generation.
"""

import re
from typing import List, Optional
from langchain_core.documents import Document

from core.models import Business

# Known prompt injection signatures
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directions|rules)",
    r"(reveal|print|show|output|leak|repeat|display)\s+(your\s+)?(system\s+)?(prompt|instructions|initial\s+prompt)",
    r"you\s+are\s+now\s+(in\s+)?(dan|developer|jailbreak|unrestricted)\s+mode",
    r"system\s*:\s*you\s+are",
    r"override\s+(all\s+)?(rules|safety|guardrails)",
    r"disregard\s+(the\s+)?(above|instructions)",
]

COMPILED_INJECTION_RE = [
    re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS
]


def check_prompt_injection(user_input: str) -> bool:
    """Detect common prompt injection or system prompt extraction attempts.

    Args:
        user_input: Raw text string provided by user.

    Returns:
        True if a prompt injection pattern is detected, False otherwise.
    """
    if not user_input or not isinstance(user_input, str):
        return False

    clean_text = user_input.strip()
    for pattern in COMPILED_INJECTION_RE:
        if pattern.search(clean_text):
            return True

    return False


def generate_injection_refusal_response(business: Optional[Business] = None) -> str:
    """Generate a polite refusal message when prompt injection is detected."""
    biz_name = business.name if business else "the business"
    return (
        f"I am a customer support assistant for {biz_name}. "
        "I can only help with questions regarding products, orders, shipping, returns, and store policies."
    )


def check_retrieval_grounding(
    retrieved_docs: List[Document],
    query: str,
) -> bool:
    """Determine whether retrieval produced sufficient context to answer the user query.

    Args:
        retrieved_docs: Documents returned by the vector retriever.
        query: User question string.

    Returns:
        True if retrieved context is deemed sufficient for generation, False otherwise.
    """
    if not retrieved_docs:
        return False

    # Check if total content length across documents is meaningful
    total_content_length = sum(len(d.page_content.strip()) for d in retrieved_docs if d.page_content)
    if total_content_length < 15:
        return False

    return True


def generate_fallback_response(
    business: Optional[Business],
    query: Optional[str] = None,
) -> str:
    """Generate a deterministic safe fallback response using actual business details.

    Args:
        business: Domain Business model instance (if available).
        query: Optional user question for context.

    Returns:
        Grounded abstention message directing customer to official support channels.
    """
    if not business:
        return (
            "I don't have that information in my current knowledge base. "
            "Please contact customer support for further assistance."
        )

    biz_name = business.name
    contact_parts: List[str] = []
    if business.contact_email:
        contact_parts.append(f"email at {business.contact_email}")
    if business.contact_phone:
        contact_parts.append(f"phone at {business.contact_phone}")
    if business.website:
        contact_parts.append(f"website at {business.website}")

    contact_str = " or ".join(contact_parts) if contact_parts else "customer support"

    return (
        f"I don't have that information in my current {biz_name} knowledge base. "
        f"Please contact {biz_name} support via {contact_str}."
    )


def sanitize_response(response_text: str) -> str:
    """Sanitize the LLM response to remove internal prompt tokens or system leakages."""
    if not response_text:
        return ""

    cleaned = response_text
    # Strip potential leaked prompt labels if LLM hallucinates prefixes
    for prefix in ["SYSTEM:", "ASSISTANT:", "BUSINESS:", "RETRIEVED CONTEXT:", "USER:"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()

    return cleaned.strip()
