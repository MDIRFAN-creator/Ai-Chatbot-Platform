"""Policy service layer for SupportBot AI.

Manages business policy creation, updates, upsert by type, and retrieval with
strict tenant scoping.
"""

from typing import Any, Dict, List, Optional, Union
from core.database import DatabaseManager, db as default_db
from core.models import Policy, PolicyCreate, PolicyUpdate


class PolicyService:
    """Service handling business policies (Shipping, Returns, Refunds, etc.)."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or default_db

    def create_policy(
        self, data: Union[PolicyCreate, Dict[str, Any]]
    ) -> Policy:
        """Create and persist a new policy."""
        model = PolicyCreate.model_validate(data) if isinstance(data, dict) else data
        return self.db.create_policy(model)

    def get_policy(
        self, policy_id: str, business_id: Optional[str] = None
    ) -> Optional[Policy]:
        """Retrieve a policy by ID."""
        if not policy_id:
            return None
        return self.db.get_policy(policy_id, business_id=business_id)

    def get_policy_by_type(
        self, business_id: str, policy_type: str
    ) -> Optional[Policy]:
        """Retrieve a specific policy by type for a business."""
        if not business_id or not policy_type:
            return None
        return self.db.get_policy_by_type(business_id, policy_type)

    def create_or_update_policy(
        self, business_id: str, policy_type: str, content: str
    ) -> Policy:
        """Create or update a policy by its type for a business."""
        cleaned_type = policy_type.strip().lower()
        existing = self.get_policy_by_type(business_id, cleaned_type)
        if existing:
            updated = self.update_policy(
                existing.policy_id,
                PolicyUpdate(content=content),
                business_id=business_id,
            )
            return updated  # type: ignore[return-value]
        return self.create_policy(
            PolicyCreate(
                business_id=business_id,
                policy_type=cleaned_type,
                content=content,
            )
        )

    def update_policy(
        self,
        policy_id: str,
        data: Union[PolicyUpdate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> Optional[Policy]:
        """Update an existing policy."""
        model = PolicyUpdate.model_validate(data) if isinstance(data, dict) else data
        return self.db.update_policy(policy_id, model, business_id=business_id)

    def delete_policy(
        self, policy_id: str, business_id: Optional[str] = None
    ) -> bool:
        """Delete a policy record."""
        return self.db.delete_policy(policy_id, business_id=business_id)

    def get_policies_by_business(self, business_id: str) -> List[Policy]:
        """Retrieve all policies belonging to a business."""
        if not business_id or not business_id.strip():
            return []
        return self.db.get_policies_by_business(business_id)


# Global default service instance
policy_service = PolicyService()
