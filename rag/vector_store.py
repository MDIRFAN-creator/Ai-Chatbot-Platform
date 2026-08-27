"""Business-Scoped FAISS Vector Store Abstraction for SupportBot AI.

Provides isolated filesystem persistence and management of FAISS vector indices
per business tenant at `vectorstore/<business_id>/faiss_index/`.
"""

import os
from pathlib import Path
import shutil
from typing import List, Optional
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from core.config import get_config


def get_business_vector_store_dir(business_id: str) -> Path:
    """Return the absolute filesystem path for a tenant's FAISS index directory."""
    if not business_id or not isinstance(business_id, str) or not business_id.strip():
        raise ValueError("A valid, non-empty business_id is required.")
    cfg = get_config()
    return cfg.vector_store_dir / business_id.strip() / "faiss_index"


def index_exists(business_id: str) -> bool:
    """Check whether a persisted FAISS index exists for the specified business."""
    index_dir = get_business_vector_store_dir(business_id)
    faiss_file = index_dir / "index.faiss"
    pkl_file = index_dir / "index.pkl"
    return index_dir.is_dir() and faiss_file.exists() and pkl_file.exists()


def create_or_replace_index(
    business_id: str,
    documents: List[Document],
    embeddings: Embeddings,
) -> Optional[FAISS]:
    """Create or overwrite a tenant-isolated FAISS vector index.

    Args:
        business_id: Unique business tenant identifier.
        documents: List of normalized LangChain Documents to index.
        embeddings: LangChain Embeddings model instance.

    Returns:
        The instantiated FAISS vector store, or None if no documents were provided.
    """
    if not business_id or not isinstance(business_id, str) or not business_id.strip():
        raise ValueError("A valid, non-empty business_id is required.")

    index_dir = get_business_vector_store_dir(business_id)

    # Clean previous index directory to prevent stale vector artifacts
    if index_dir.exists():
        shutil.rmtree(index_dir, ignore_errors=True)

    if not documents:
        return None

    # Verify all documents carry the correct business_id
    clean_bid = business_id.strip()
    for doc in documents:
        doc_bid = doc.metadata.get("business_id")
        if doc_bid != clean_bid:
            raise ValueError(
                f"Document tenant mismatch: expected business_id '{clean_bid}', got '{doc_bid}'"
            )

    index_dir.mkdir(parents=True, exist_ok=True)
    vector_store = FAISS.from_documents(documents=documents, embedding=embeddings)
    vector_store.save_local(folder_path=str(index_dir))
    return vector_store


def load_index(
    business_id: str,
    embeddings: Embeddings,
) -> Optional[FAISS]:
    """Load an existing persisted FAISS index for a business tenant.

    Args:
        business_id: Unique business tenant identifier.
        embeddings: LangChain Embeddings model instance.

    Returns:
        Loaded FAISS vector store, or None if no index exists for this business.
    """
    if not index_exists(business_id):
        return None

    index_dir = get_business_vector_store_dir(business_id)
    return FAISS.load_local(
        folder_path=str(index_dir),
        embeddings=embeddings,
        allow_dangerous_deserialization=True,
    )


def delete_index(business_id: str) -> bool:
    """Delete a tenant's FAISS index from disk."""
    index_dir = get_business_vector_store_dir(business_id)
    tenant_root = index_dir.parent  # vectorstore/<business_id>
    if tenant_root.exists():
        shutil.rmtree(tenant_root, ignore_errors=True)
        return True
    return False
