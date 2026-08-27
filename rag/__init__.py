"""RAG (Retrieval-Augmented Generation) Infrastructure Package for SupportBot AI."""

from rag.chain import RAGChain, RAGResponse
from rag.embeddings import get_embedding_dimension, get_embedding_model
from rag.guardrails import (
    check_prompt_injection,
    check_retrieval_grounding,
    generate_fallback_response,
    generate_injection_refusal_response,
    sanitize_response,
)
from rag.llm import get_llm
from rag.memory import ConversationMemory
from rag.prompts import (
    build_rag_prompt_messages,
    format_assistant_context,
    format_business_context,
    format_conversation_history,
    format_retrieved_context,
    get_rag_chat_prompt_template,
)
from rag.retriever import retrieve, retrieve_with_scores
from rag.vector_store import (
    create_or_replace_index,
    delete_index,
    get_business_vector_store_dir,
    index_exists,
    load_index,
)

__all__ = [
    "get_embedding_model",
    "get_embedding_dimension",
    "get_business_vector_store_dir",
    "index_exists",
    "create_or_replace_index",
    "load_index",
    "delete_index",
    "retrieve",
    "retrieve_with_scores",
    "get_llm",
    "ConversationMemory",
    "check_prompt_injection",
    "check_retrieval_grounding",
    "generate_fallback_response",
    "generate_injection_refusal_response",
    "sanitize_response",
    "format_business_context",
    "format_assistant_context",
    "format_retrieved_context",
    "format_conversation_history",
    "build_rag_prompt_messages",
    "get_rag_chat_prompt_template",
    "RAGChain",
    "RAGResponse",
]
