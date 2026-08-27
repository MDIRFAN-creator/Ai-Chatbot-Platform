"""LLM Provider Abstraction for SupportBot AI.

Provides a unified interface for instantiating chat models, primarily Gemini
via `langchain_google_genai.ChatGoogleGenerativeAI`, respecting application configuration.
"""

from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from core.config import get_config


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    api_key: Optional[str] = None,
) -> BaseChatModel:
    """Instantiate and return the configured Chat LLM.

    Args:
        provider: LLM provider name (defaults to config.llm_provider).
        model: Model name / identifier (defaults to config.llm_model).
        temperature: Generation temperature (defaults to config.llm_temperature).
        api_key: Optional API key override (defaults to config.gemini_api_key).

    Returns:
        Configured BaseChatModel instance.

    Raises:
        ValueError: If provider is 'gemini' and no GEMINI_API_KEY is available.
    """
    cfg = get_config()
    target_provider = provider or cfg.llm_provider
    target_model = model or cfg.llm_model
    target_temp = temperature if temperature is not None else cfg.llm_temperature
    target_key = api_key if api_key is not None else cfg.gemini_api_key

    if target_provider == "gemini":
        if not target_key or not target_key.strip():
            raise ValueError(
                "GEMINI_API_KEY is not configured in environment. "
                "Please set GEMINI_API_KEY in your .env file to enable Gemini generation."
            )

        return ChatGoogleGenerativeAI(
            model=target_model,
            google_api_key=target_key,
            temperature=target_temp,
        )

    # Future provider extensibility fallback
    raise ValueError(f"Unsupported LLM provider: {target_provider}")
