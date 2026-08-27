"""Local Embedding Provider Abstraction for SupportBot AI.

Centralizes local Hugging Face embedding model initialization and caching
using sentence-transformers/all-MiniLM-L6-v2 (384 dimensions).
"""

from typing import Optional
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from core.config import get_config

# Global singleton cache for embedding models
_EMBEDDING_MODEL_CACHE: dict = {}


def get_embedding_model(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Embeddings:
    """Retrieve or initialize a cached local Hugging Face embedding model.

    Args:
        provider: Embedding provider name (defaults to config.embedding_provider).
        model_name: Model identifier (defaults to config.embedding_model).

    Returns:
        Configured LangChain Embeddings instance.
    """
    cfg = get_config()
    target_provider = provider or cfg.embedding_provider
    target_model = model_name or cfg.embedding_model

    cache_key = f"{target_provider}:{target_model}"
    if cache_key in _EMBEDDING_MODEL_CACHE:
        return _EMBEDDING_MODEL_CACHE[cache_key]

    if target_provider == "huggingface_local":
        embeddings = HuggingFaceEmbeddings(
            model_name=target_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    else:
        # Fallback or future provider extensibility
        embeddings = HuggingFaceEmbeddings(
            model_name=target_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    _EMBEDDING_MODEL_CACHE[cache_key] = embeddings
    return embeddings


def get_embedding_dimension(embeddings: Optional[Embeddings] = None) -> int:
    """Return the output vector dimension for the configured embedding model.

    For sentence-transformers/all-MiniLM-L6-v2, the dimension is 384.
    """
    model = embeddings or get_embedding_model()
    # Embed a short probe query to determine dimension
    probe_vec = model.embed_query("probe")
    return len(probe_vec)
