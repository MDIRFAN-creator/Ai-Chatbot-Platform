"""Assistant service layer for SupportBot AI.

Manages AI assistant configuration (name, tone, welcome message) respecting
the 1:1 business relationship.
"""

from typing import Any, Dict, Optional, Union
from core.database import DatabaseManager, db as default_db
from core.models import (
    AssistantSettings,
    AssistantSettingsCreate,
    AssistantSettingsUpdate,
)


class AssistantService:
    """Service handling assistant configuration."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or default_db

    def get_assistant_settings(
        self, business_id: str
    ) -> Optional[AssistantSettings]:
        """Retrieve assistant settings for a business."""
        if not business_id or not business_id.strip():
            return None
        return self.db.get_assistant_settings(business_id)

    def create_or_update_assistant_settings(
        self,
        data: Union[AssistantSettingsCreate, AssistantSettingsUpdate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> AssistantSettings:
        """Create or update assistant settings for a business."""
        return self.db.create_or_update_assistant_settings(
            data, business_id=business_id
        )

    def delete_assistant_settings(self, business_id: str) -> bool:
        """Delete assistant settings for a business."""
        if not business_id or not business_id.strip():
            return False
        return self.db.delete_assistant_settings(business_id)


# Global default service instance
assistant_service = AssistantService()
