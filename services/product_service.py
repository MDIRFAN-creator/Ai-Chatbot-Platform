"""Product service layer for SupportBot AI.

Manages product catalog CRUD operations with strict tenant (business_id) isolation.
"""

from typing import Any, Dict, List, Optional, Union
from core.database import DatabaseManager, db as default_db
from core.models import Product, ProductCreate, ProductUpdate


class ProductService:
    """Service handling product catalog operations."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or default_db

    def create_product(
        self, data: Union[ProductCreate, Dict[str, Any]]
    ) -> Product:
        """Create and persist a new product for a business."""
        model = ProductCreate.model_validate(data) if isinstance(data, dict) else data
        return self.db.create_product(model)

    def get_product(
        self, product_id: str, business_id: Optional[str] = None
    ) -> Optional[Product]:
        """Retrieve a product by ID, optionally scoped to business_id."""
        if not product_id:
            return None
        return self.db.get_product(product_id, business_id=business_id)

    def update_product(
        self,
        product_id: str,
        data: Union[ProductUpdate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> Optional[Product]:
        """Update a product with business_id validation."""
        model = ProductUpdate.model_validate(data) if isinstance(data, dict) else data
        return self.db.update_product(product_id, model, business_id=business_id)

    def delete_product(
        self, product_id: str, business_id: Optional[str] = None
    ) -> bool:
        """Delete a product belonging to a specific business."""
        return self.db.delete_product(product_id, business_id=business_id)

    def get_products_by_business(self, business_id: str) -> List[Product]:
        """Retrieve all products strictly scoped to a business."""
        if not business_id or not business_id.strip():
            return []
        return self.db.get_products_by_business(business_id)


# Global default service instance
product_service = ProductService()
