"""Unit tests for SupportBot AI Service Layer (Phase 3).

Tests:
- BusinessService: creation, retrieval, update, listing, deletion
- ProductService: CRUD, JSON parsing, tenant scoping & isolation
- PolicyService: CRUD, create_or_update by type, tenant isolation
- FAQService: CRUD, tenant scoping & isolation
- AssistantService: CRUD, upsert, 1:1 business relationship
- Validation error propagation and error handling
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from core.database import DatabaseManager
from core.models import (
    AssistantSettingsCreate,
    AssistantSettingsUpdate,
    BusinessCreate,
    BusinessUpdate,
    FAQCreate,
    FAQUpdate,
    PolicyCreate,
    PolicyUpdate,
    ProductCreate,
    ProductUpdate,
)
from services.assistant_service import AssistantService
from services.business_service import BusinessService
from services.faq_service import FAQService
from services.policy_service import PolicyService
from services.product_service import ProductService


@pytest.fixture
def test_db(tmp_path: Path) -> DatabaseManager:
    """Create and initialize a temporary test database."""
    db_file = tmp_path / "test_services.db"
    db_mgr = DatabaseManager(db_file)
    db_mgr.initialize()
    return db_mgr


@pytest.fixture
def services(test_db: DatabaseManager):
    """Return all service instances wired to the temporary test database."""
    return {
        "business": BusinessService(test_db),
        "product": ProductService(test_db),
        "policy": PolicyService(test_db),
        "faq": FAQService(test_db),
        "assistant": AssistantService(test_db),
    }


# =====================================================================
# 1. BUSINESS SERVICE TESTS
# =====================================================================

def test_business_service_crud(services):
    """Test business creation, retrieval, updating, and listing."""
    bs: BusinessService = services["business"]

    # Create
    biz = bs.create_business(
        BusinessCreate(
            name="Alpha Store",
            description="Premium goods",
            industry="Retail",
            website="https://alpha.example.com",
            contact_email="support@alpha.example.com",
        )
    )
    assert biz.business_id is not None
    assert biz.name == "Alpha Store"

    # Get
    fetched = bs.get_business(biz.business_id)
    assert fetched is not None
    assert fetched.name == "Alpha Store"
    assert fetched.website == "https://alpha.example.com"

    # Update
    updated = bs.update_business(
        biz.business_id,
        BusinessUpdate(description="Updated luxury goods", location="Austin, TX"),
    )
    assert updated is not None
    assert updated.description == "Updated luxury goods"
    assert updated.location == "Austin, TX"

    # List
    all_biz = bs.list_businesses()
    assert len(all_biz) == 1
    assert all_biz[0].business_id == biz.business_id

    # Delete
    assert bs.delete_business(biz.business_id) is True
    assert bs.get_business(biz.business_id) is None


# =====================================================================
# 2. PRODUCT SERVICE TESTS & TENANT ISOLATION
# =====================================================================

def test_product_service_crud_and_isolation(services):
    """Test product creation, update, delete, and strict tenant isolation."""
    bs: BusinessService = services["business"]
    ps: ProductService = services["product"]

    biz1 = bs.create_business(BusinessCreate(name="Store One"))
    biz2 = bs.create_business(BusinessCreate(name="Store Two"))

    # Create products for each business
    p1 = ps.create_product(
        ProductCreate(
            business_id=biz1.business_id,
            name="Sneakers",
            price=99.99,
            sizes=["8", "9", "10"],
            colors=["White", "Black"],
        )
    )
    p2 = ps.create_product(
        ProductCreate(
            business_id=biz2.business_id,
            name="Handbag",
            price=149.99,
            sizes=["One Size"],
            colors=["Brown"],
        )
    )

    # Scoped retrieval
    b1_products = ps.get_products_by_business(biz1.business_id)
    assert len(b1_products) == 1
    assert b1_products[0].name == "Sneakers"
    assert b1_products[0].sizes == ["8", "9", "10"]

    b2_products = ps.get_products_by_business(biz2.business_id)
    assert len(b2_products) == 1
    assert b2_products[0].name == "Handbag"

    # Cross-tenant get with verification
    assert ps.get_product(p1.product_id, business_id=biz2.business_id) is None
    assert ps.get_product(p2.product_id, business_id=biz1.business_id) is None

    # Update product
    updated = ps.update_product(
        p1.product_id,
        ProductUpdate(price=89.99, availability="low_stock"),
        business_id=biz1.business_id,
    )
    assert updated is not None
    assert updated.price == 89.99
    assert updated.availability == "low_stock"

    # Unauthorized cross-tenant update should fail
    unauth_update = ps.update_product(
        p1.product_id,
        ProductUpdate(name="Hacked Name"),
        business_id=biz2.business_id,
    )
    assert unauth_update is None
    orig_p1 = ps.get_product(p1.product_id)
    assert orig_p1 is not None
    assert orig_p1.name == "Sneakers"

    # Delete product
    assert ps.delete_product(p1.product_id, business_id=biz1.business_id) is True
    assert len(ps.get_products_by_business(biz1.business_id)) == 0


# =====================================================================
# 3. POLICY SERVICE TESTS & UPSERT BY TYPE
# =====================================================================

def test_policy_service_crud_and_upsert(services):
    """Test policy creation, retrieval, upsert by type, and tenant isolation."""
    bs: BusinessService = services["business"]
    pols: PolicyService = services["policy"]

    biz1 = bs.create_business(BusinessCreate(name="Policy Biz 1"))
    biz2 = bs.create_business(BusinessCreate(name="Policy Biz 2"))

    # Create or update policy
    pol1 = pols.create_or_update_policy(
        business_id=biz1.business_id,
        policy_type="shipping",
        content="Free shipping on orders over $50.",
    )
    assert pol1.policy_type == "shipping"
    assert pol1.content == "Free shipping on orders over $50."

    # Update the same policy via upsert
    pol1_updated = pols.create_or_update_policy(
        business_id=biz1.business_id,
        policy_type="shipping",
        content="Free 2-day shipping on all orders.",
    )
    assert pol1_updated.policy_id == pol1.policy_id
    assert pol1_updated.content == "Free 2-day shipping on all orders."

    # Verify business 2 does not have shipping policy
    assert pols.get_policy_by_type(biz2.business_id, "shipping") is None

    # Retrieve all policies for business 1
    pols.create_or_update_policy(biz1.business_id, "returns", "30-day return window.")
    all_p1 = pols.get_policies_by_business(biz1.business_id)
    assert len(all_p1) == 2


# =====================================================================
# 4. FAQ SERVICE TESTS & TENANT ISOLATION
# =====================================================================

def test_faq_service_crud_and_isolation(services):
    """Test FAQ creation, update, delete, and business isolation."""
    bs: BusinessService = services["business"]
    faqs: FAQService = services["faq"]

    biz1 = bs.create_business(BusinessCreate(name="FAQ Store 1"))
    biz2 = bs.create_business(BusinessCreate(name="FAQ Store 2"))

    faq1 = faqs.create_faq(
        FAQCreate(
            business_id=biz1.business_id,
            question="Do you offer gift wrapping?",
            answer="Yes, at checkout for $5.",
        )
    )
    assert faq1.faq_id is not None

    # Isolation
    assert len(faqs.get_faqs_by_business(biz1.business_id)) == 1
    assert len(faqs.get_faqs_by_business(biz2.business_id)) == 0

    # Update
    updated = faqs.update_faq(
        faq1.faq_id,
        FAQUpdate(answer="Yes, complimentary gift wrapping is available."),
        business_id=biz1.business_id,
    )
    assert updated is not None
    assert updated.answer == "Yes, complimentary gift wrapping is available."

    # Delete
    assert faqs.delete_faq(faq1.faq_id, business_id=biz1.business_id) is True
    assert len(faqs.get_faqs_by_business(biz1.business_id)) == 0


# =====================================================================
# 5. ASSISTANT SERVICE TESTS (1:1 per Business)
# =====================================================================

def test_assistant_service_config(services):
    """Test assistant settings configuration and upsert behavior."""
    bs: BusinessService = services["business"]
    assts: AssistantService = services["assistant"]

    biz = bs.create_business(BusinessCreate(name="Support Brand"))

    # Initial get
    assert assts.get_assistant_settings(biz.business_id) is None

    # Create
    asst = assts.create_or_update_assistant_settings(
        AssistantSettingsCreate(
            business_id=biz.business_id,
            assistant_name="SupportBot AI",
            tone="friendly and professional",
            welcome_message="Hello! How can I assist you today?",
        )
    )
    assert asst.assistant_name == "SupportBot AI"
    assert asst.business_id == biz.business_id

    # Update
    updated = assts.create_or_update_assistant_settings(
        AssistantSettingsUpdate(assistant_name="SupportBot Pro", tone="expert"),
        business_id=biz.business_id,
    )
    assert updated.assistant_name == "SupportBot Pro"
    assert updated.tone == "expert"
    assert updated.welcome_message == "Hello! How can I assist you today?"
    assert updated.assistant_id == asst.assistant_id


# =====================================================================
# 6. VALIDATION HANDLING TESTS
# =====================================================================

def test_validation_errors(services):
    """Test that invalid data triggers Pydantic validation errors."""
    bs: BusinessService = services["business"]
    ps: ProductService = services["product"]

    # Empty business name
    with pytest.raises(ValidationError):
        bs.create_business(BusinessCreate(name=""))

    # Negative product price
    with pytest.raises(ValidationError):
        ps.create_product(
            ProductCreate(business_id="any_biz", name="Invalid Product", price=-10.0)
        )
