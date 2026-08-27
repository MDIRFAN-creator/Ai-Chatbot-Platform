"""Knowledge Manager for SupportBot AI.

Coordinates the end-to-end knowledge base generation pipeline:
SQLite -> DocumentLoader -> DocumentBuilder -> SQLite Persistence -> Embeddings -> FAISS Index.
"""

from typing import Any, Dict, List, Optional

from core.config import get_config
from core.database import DatabaseManager
from core.models import KnowledgeDocument, KnowledgeDocumentCreate
from knowledge.document_builder import build_all_documents
from knowledge.document_loader import DocumentLoader
from rag.embeddings import get_embedding_model
from rag.vector_store import (
    create_or_replace_index,
    delete_index,
    get_business_vector_store_dir,
    index_exists,
)


class KnowledgeManager:
    """Orchestrates document building, SQLite normalization, and FAISS indexing."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        loader: Optional[DocumentLoader] = None,
    ):
        self.db = db_manager or DatabaseManager()
        self.loader = loader or DocumentLoader(self.db)

    def build_knowledge_base(
        self,
        business_id: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a full rebuild of a business tenant's knowledge base.

        Steps:
            1. Load current structured records from SQLite.
            2. Normalize into LangChain Documents with configurable chunking.
            3. Purge existing knowledge_documents for this business in SQLite.
            4. Persist new normalized documents into SQLite knowledge_documents.
            5. Obtain local Hugging Face embeddings model.
            6. Build and persist the business-scoped FAISS vector index.

        Args:
            business_id: Unique business tenant identifier.
            chunk_size: Optional custom chunk size override.
            chunk_overlap: Optional custom chunk overlap override.

        Returns:
            Dict containing build statistics, document counts, and index status.
        """
        if not business_id or not isinstance(business_id, str) or not business_id.strip():
            raise ValueError("A valid, non-empty business_id is required.")

        clean_bid = business_id.strip()

        # 1. Load structured source data
        source_data = self.loader.load_business_source_data(clean_bid)
        business = source_data["business"]
        products = source_data["products"]
        policies = source_data["policies"]
        faqs = source_data["faqs"]

        # 2. Build normalized LangChain Documents
        documents = build_all_documents(
            business=business,
            products=products,
            policies=policies,
            faqs=faqs,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # 3. Purge stale normalized records in SQLite
        deleted_count = self.db.delete_knowledge_documents_by_business(clean_bid)

        # 4. Persist newly normalized records into SQLite knowledge_documents
        persisted_docs: List[KnowledgeDocument] = []
        for doc in documents:
            source_type = doc.metadata.get("source_type", "unknown")
            source_id = doc.metadata.get("source_id", clean_bid)
            kdoc_create = KnowledgeDocumentCreate(
                business_id=clean_bid,
                source_type=source_type,
                source_id=source_id,
                content=doc.page_content,
                metadata=doc.metadata,
            )
            created_kdoc = self.db.create_knowledge_document(kdoc_create)
            persisted_docs.append(created_kdoc)

        # 5. Obtain local embedding model
        embeddings = get_embedding_model()

        # 6. Rebuild and persist business-scoped FAISS index
        vector_store = create_or_replace_index(
            business_id=clean_bid,
            documents=documents,
            embeddings=embeddings,
        )

        index_dir = get_business_vector_store_dir(clean_bid)

        return {
            "business_id": clean_bid,
            "status": "success" if vector_store is not None or not documents else "empty",
            "source_counts": {
                "business": 1 if business else 0,
                "products": len(products),
                "policies": len(policies),
                "faqs": len(faqs),
            },
            "normalized_documents_count": len(persisted_docs),
            "stale_documents_purged": deleted_count,
            "faiss_index_ready": index_exists(clean_bid),
            "vector_store_path": str(index_dir),
        }

    def delete_knowledge_base(self, business_id: str) -> bool:
        """Delete all normalized knowledge documents and FAISS index for a business."""
        if not business_id or not isinstance(business_id, str) or not business_id.strip():
            raise ValueError("A valid, non-empty business_id is required.")

        clean_bid = business_id.strip()
        self.db.delete_knowledge_documents_by_business(clean_bid)
        delete_index(clean_bid)
        return True

    def get_knowledge_base_status(self, business_id: str) -> Dict[str, Any]:
        """Return the current knowledge base status and counts for a business."""
        if not business_id or not isinstance(business_id, str) or not business_id.strip():
            raise ValueError("A valid, non-empty business_id is required.")

        clean_bid = business_id.strip()
        source_data = self.loader.load_business_source_data(clean_bid)
        kdocs = self.db.get_knowledge_documents_by_business(clean_bid)
        has_index = index_exists(clean_bid)
        index_dir = get_business_vector_store_dir(clean_bid)

        return {
            "business_id": clean_bid,
            "business_configured": source_data["business"] is not None,
            "source_counts": {
                "business": 1 if source_data["business"] else 0,
                "products": len(source_data["products"]),
                "policies": len(source_data["policies"]),
                "faqs": len(source_data["faqs"]),
            },
            "normalized_documents_count": len(kdocs),
            "faiss_index_ready": has_index,
            "vector_store_path": str(index_dir),
        }
