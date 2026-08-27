"""Business-Scoped Vector Retriever for SupportBot AI.

Provides strictly tenant-isolated similarity search over FAISS vector indices
located at `vectorstore/<business_id>/faiss_index/`.
"""

from typing import List, Optional, Tuple
from langchain_core.documents import Document

from core.config import get_config
from rag.embeddings import get_embedding_model
from rag.vector_store import index_exists, load_index


def retrieve_with_scores(
    query: str,
    business_id: str,
    top_k: Optional[int] = None,
) -> List[Tuple[Document, float]]:
    """Retrieve top-k documents with FAISS similarity scores for a specific business tenant.

    Args:
        query: User question or search query string.
        business_id: Unique identifier for the business tenant.
        top_k: Number of documents to retrieve (defaults to config.retrieval_top_k).

    Returns:
        List of (Document, score) tuples, or empty list if index does not exist or query is empty.

    Raises:
        ValueError: If business_id is missing or empty.
    """
    if not business_id or not isinstance(business_id, str) or not business_id.strip():
        raise ValueError("A valid, non-empty business_id is required for retrieval.")

    if not query or not isinstance(query, str) or not query.strip():
        return []

    clean_bid = business_id.strip()
    clean_query = query.strip()

    if not index_exists(clean_bid):
        return []

    cfg = get_config()
    k = top_k if top_k is not None and top_k > 0 else cfg.retrieval_top_k

    embeddings = get_embedding_model()
    vector_store = load_index(clean_bid, embeddings)
    if vector_store is None:
        return []

    # Perform similarity search with score
    results = vector_store.similarity_search_with_score(clean_query, k=k)

    # Validate that all retrieved documents strictly belong to this business
    filtered_results: List[Tuple[Document, float]] = []
    for doc, score in results:
        doc_bid = doc.metadata.get("business_id")
        if doc_bid == clean_bid:
            filtered_results.append((doc, float(score)))

    return filtered_results


def retrieve(
    query: str,
    business_id: str,
    top_k: Optional[int] = None,
    relevance_threshold: Optional[float] = None,
) -> List[Document]:
    """Retrieve top-k relevant documents strictly belonging to the requested business.

    Args:
        query: User question or search query string.
        business_id: Unique identifier for the business tenant.
        top_k: Number of documents to retrieve (defaults to config.retrieval_top_k).
        relevance_threshold: Optional maximum distance / score threshold filter.

    Returns:
        List of LangChain Document objects.
    """
    scored_results = retrieve_with_scores(query, business_id, top_k=top_k)

    cfg = get_config()
    thresh = relevance_threshold if relevance_threshold is not None else cfg.relevance_score_threshold

    if thresh is not None:
        # FAISS distance score: lower is closer. Filter out documents exceeding threshold
        return [doc for doc, score in scored_results if score <= thresh]

    return [doc for doc, _ in scored_results]
