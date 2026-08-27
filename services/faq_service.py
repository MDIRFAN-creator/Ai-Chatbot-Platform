"""FAQ service layer for SupportBot AI.

Manages frequently asked questions (FAQs) CRUD operations with business scoping.
"""

from typing import Any, Dict, List, Optional, Union
from core.database import DatabaseManager, db as default_db
from core.models import FAQ, FAQCreate, FAQUpdate


class FAQService:
    """Service handling FAQ operations."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or default_db

    def create_faq(self, data: Union[FAQCreate, Dict[str, Any]]) -> FAQ:
        """Create and persist a new FAQ."""
        model = FAQCreate.model_validate(data) if isinstance(data, dict) else data
        return self.db.create_faq(model)

    def get_faq(
        self, faq_id: str, business_id: Optional[str] = None
    ) -> Optional[FAQ]:
        """Retrieve an FAQ by ID."""
        if not faq_id:
            return None
        return self.db.get_faq(faq_id, business_id=business_id)

    def update_faq(
        self,
        faq_id: str,
        data: Union[FAQUpdate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> Optional[FAQ]:
        """Update an existing FAQ."""
        model = FAQUpdate.model_validate(data) if isinstance(data, dict) else data
        return self.db.update_faq(faq_id, model, business_id=business_id)

    def delete_faq(
        self, faq_id: str, business_id: Optional[str] = None
    ) -> bool:
        """Delete an FAQ."""
        return self.db.delete_faq(faq_id, business_id=business_id)

    def get_faqs_by_business(self, business_id: str) -> List[FAQ]:
        """Retrieve all FAQs belonging to a specific business."""
        if not business_id or not business_id.strip():
            return []
        return self.db.get_faqs_by_business(business_id)


# Global default service instance
faq_service = FAQService()
