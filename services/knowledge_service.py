"""Knowledge Service business logic layer for SupportBot AI.

Provides application-facing operations for building, inspecting, and managing
tenant-isolated knowledge bases.
"""

from typing import Any, Dict, List, Optional

from core.database import DatabaseManager
from core.models import KnowledgeDocument
from knowledge.knowledge_manager import KnowledgeManager


class KnowledgeService:
    """Service layer for business-scoped knowledge base generation and management."""

    def __init__(
        self,
        manager: Optional[KnowledgeManager] = None,
        db_manager: Optional[DatabaseManager] = None,
    ):
        self.db = db_manager or DatabaseManager()
        self.manager = manager or KnowledgeManager(self.db)

    def build_knowledge_base(
        self,
        business_id: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Trigger a complete knowledge base build/regeneration for a business."""
        return self.manager.build_knowledge_base(
            business_id=business_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def get_knowledge_base_status(self, business_id: str) -> Dict[str, Any]:
        """Retrieve the current knowledge base status, counts, and FAISS index readiness."""
        return self.manager.get_knowledge_base_status(business_id)

    def delete_knowledge_base(self, business_id: str) -> bool:
        """Delete all normalized knowledge documents and the FAISS index for a business."""
        return self.manager.delete_knowledge_base(business_id)

    def get_knowledge_documents(self, business_id: str) -> List[KnowledgeDocument]:
        """Retrieve all normalized knowledge documents persisted in SQLite for a business."""
        return self.db.get_knowledge_documents_by_business(business_id)


# Global singleton service instance
knowledge_service = KnowledgeService()
