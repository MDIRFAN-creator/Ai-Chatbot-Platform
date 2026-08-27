"""Document Loader for SupportBot AI Knowledge Base.

Loads structured source records from SQLite for a given business tenant
using the established service / database repository abstractions.
"""

from typing import Any, Dict, List, Optional
from core.database import DatabaseManager
from core.models import Business, FAQ, Policy, Product


class DocumentLoader:
    """Loads structured tenant entities for knowledge document generation."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def load_business_source_data(self, business_id: str) -> Dict[str, Any]:
        """Load all structured source records strictly belonging to the specified business.

        Args:
            business_id: The unique identifier of the business tenant.

        Returns:
            Dict containing:
                - "business": Optional[Business]
                - "products": List[Product]
                - "policies": List[Policy]
                - "faqs": List[FAQ]
        """
        if not business_id or not isinstance(business_id, str) or not business_id.strip():
            raise ValueError("A valid, non-empty business_id is required to load source data.")

        clean_bid = business_id.strip()

        business = self.db.get_business(clean_bid)
        products = self.db.get_products_by_business(clean_bid)
        policies = self.db.get_policies_by_business(clean_bid)
        faqs = self.db.get_faqs_by_business(clean_bid)

        return {
            "business": business,
            "products": products,
            "policies": policies,
            "faqs": faqs,
        }
