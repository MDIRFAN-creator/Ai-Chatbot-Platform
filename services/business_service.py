"""Business service layer for SupportBot AI.

Provides business profile onboarding, retrieval, updating, and listing operations
interacting with the database layer.
"""

from typing import Any, Dict, List, Optional, Union
from core.database import DatabaseManager, db as default_db
from core.models import Business, BusinessCreate, BusinessUpdate


class BusinessService:
    """Service handling business entity operations."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or default_db

    def create_business(
        self, data: Union[BusinessCreate, Dict[str, Any]]
    ) -> Business:
        """Create and persist a new business."""
        model = BusinessCreate.model_validate(data) if isinstance(data, dict) else data
        return self.db.create_business(model)

    def get_business(self, business_id: str) -> Optional[Business]:
        """Retrieve a business by ID."""
        if not business_id or not business_id.strip():
            return None
        return self.db.get_business(business_id)

    def update_business(
        self, business_id: str, data: Union[BusinessUpdate, Dict[str, Any]]
    ) -> Optional[Business]:
        """Update an existing business record."""
        model = BusinessUpdate.model_validate(data) if isinstance(data, dict) else data
        return self.db.update_business(business_id, model)

    def delete_business(self, business_id: str) -> bool:
        """Delete a business and all associated child entities."""
        return self.db.delete_business(business_id)

    def list_businesses(self) -> List[Business]:
        """Retrieve all businesses registered on the platform."""
        return self.db.list_businesses()


# Global default service instance
business_service = BusinessService()
