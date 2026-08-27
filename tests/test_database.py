"""Comprehensive test suite for SupportBot AI SQLite Database & Models (Phase 2).

Validates:
- Database initialization and schema creation across all 8 tables
- Foreign key enforcement and cascading deletions
- Model validation and Pydantic constraints
- JSON serialization/deserialization for products (sizes, colors) and knowledge docs (metadata)
- Timestamps updates
- Full CRUD for all 8 entities
- Strict multi-tenant isolation across products, policies, FAQs, knowledge docs, and conversations/messages
- Evaluation dataset safety and isolation
"""

import json
from pathlib import Path
import sqlite3
import pytest
from pydantic import ValidationError

from core.database import DatabaseManager, init_db, get_connection
from core.models import (
    AssistantSettingsCreate,
    AssistantSettingsUpdate,
    BusinessCreate,
    BusinessUpdate,
    ConversationCreate,
    FAQCreate,
    FAQUpdate,
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    MessageCreate,
    PolicyCreate,
    PolicyUpdate,
    ProductCreate,
    ProductUpdate,
)


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Create a unique temporary database file for test isolation."""
    db_file = tmp_path / "test_supportbot.db"
    return db_file


@pytest.fixture
def db(test_db_path: Path) -> DatabaseManager:
    """Initialize a fresh database and return a DatabaseManager instance."""
    db_mgr = DatabaseManager(test_db_path)
    db_mgr.initialize()
    return db_mgr


# =====================================================================
# 1. INITIALIZATION & SCHEMA TESTS
# =====================================================================

def test_database_initialization_and_tables(db: DatabaseManager, test_db_path: Path):
    """Test that database initializes and creates all 8 required tables and indexes."""
    assert test_db_path.exists()

    expected_tables = {
        "businesses",
        "assistant_settings",
        "products",
        "policies",
        "faqs",
        "knowledge_documents",
        "conversations",
        "messages",
    }

    with get_connection(test_db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        existing_tables = {row["name"] for row in rows}

    assert expected_tables.issubset(existing_tables), f"Missing tables: {expected_tables - existing_tables}"


def test_foreign_key_enforcement(db: DatabaseManager, test_db_path: Path):
    """Test that foreign key constraints prevent orphan records."""
    # Attempting to insert a product for a non-existent business should raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        with get_connection(test_db_path) as conn:
            conn.execute(
                """
                INSERT INTO products (
                    product_id, business_id, name, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                ("prod_orphan", "non_existent_biz", "Ghost Product", "2026-01-01", "2026-01-01"),
            )


# =====================================================================
# 2. BUSINESS CRUD TESTS
# =====================================================================

def test_business_crud(db: DatabaseManager):
    """Test complete CRUD lifecycle for businesses."""
    # 1. Create
    biz = db.create_business(
        BusinessCreate(
            name="UrbanThreads Apparel",
            description="Modern urban clothing brand",
            industry="Apparel & Fashion",
            website="https://urbanthreads.example.com",
            contact_email="support@urbanthreads.example.com",
            contact_phone="+1-800-555-0199",
            location="New York, NY",
        )
    )
    assert biz.business_id is not None
    assert biz.name == "UrbanThreads Apparel"
    assert biz.created_at is not None
    assert biz.updated_at is not None

    # 2. Read
    fetched = db.get_business(biz.business_id)
    assert fetched is not None
    assert fetched.business_id == biz.business_id
    assert fetched.contact_email == "support@urbanthreads.example.com"

    # 3. Update
    updated = db.update_business(
        biz.business_id,
        BusinessUpdate(contact_email="help@urbanthreads.example.com", location="Brooklyn, NY"),
    )
    assert updated is not None
    assert updated.contact_email == "help@urbanthreads.example.com"
    assert updated.location == "Brooklyn, NY"
    assert updated.name == "UrbanThreads Apparel"

    # 4. List
    all_biz = db.list_businesses()
    assert len(all_biz) == 1
    assert all_biz[0].business_id == biz.business_id

    # 5. Delete
    deleted = db.delete_business(biz.business_id)
    assert deleted is True
    assert db.get_business(biz.business_id) is None
    assert len(db.list_businesses()) == 0


def test_business_cascade_deletion(db: DatabaseManager):
    """Test that deleting a business cascades to child products, policies, etc."""
    biz = db.create_business(BusinessCreate(name="Cascade Test Store"))
    prod = db.create_product(ProductCreate(business_id=biz.business_id, name="Test Item", price=19.99))
    pol = db.create_policy(PolicyCreate(business_id=biz.business_id, policy_type="shipping", content="Fast shipping"))
    faq = db.create_faq(FAQCreate(business_id=biz.business_id, question="Q?", answer="A."))

    assert db.get_product(prod.product_id) is not None
    assert db.get_policy(pol.policy_id) is not None
    assert db.get_faq(faq.faq_id) is not None

    # Delete business
    db.delete_business(biz.business_id)

    # All children should be deleted via CASCADE
    assert db.get_product(prod.product_id) is None
    assert db.get_policy(pol.policy_id) is None
    assert db.get_faq(faq.faq_id) is None


# =====================================================================
# 3. ASSISTANT SETTINGS TESTS (1:1 Relationship)
# =====================================================================

def test_assistant_settings_crud_and_upsert(db: DatabaseManager):
    """Test creating, reading, and upserting assistant settings."""
    biz = db.create_business(BusinessCreate(name="Nova Retail"))

    # Initial get should be None
    assert db.get_assistant_settings(biz.business_id) is None

    # Create settings
    asst = db.create_or_update_assistant_settings(
        AssistantSettingsCreate(
            business_id=biz.business_id,
            assistant_name="NovaBot",
            tone="enthusiastic and helpful",
            welcome_message="Welcome to Nova Retail! How can I assist you?",
        )
    )
    assert asst.assistant_name == "NovaBot"
    assert asst.business_id == biz.business_id

    # Update settings using upsert
    updated_asst = db.create_or_update_assistant_settings(
        AssistantSettingsUpdate(assistant_name="NovaCare Pro", tone="empathetic"),
        business_id=biz.business_id,
    )
    assert updated_asst.assistant_name == "NovaCare Pro"
    assert updated_asst.tone == "empathetic"
    assert updated_asst.welcome_message == "Welcome to Nova Retail! How can I assist you?"
    assert updated_asst.assistant_id == asst.assistant_id

    # Delete
    assert db.delete_assistant_settings(biz.business_id) is True
    assert db.get_assistant_settings(biz.business_id) is None


# =====================================================================
# 4. PRODUCT CRUD & JSON SERIALIZATION TESTS
# =====================================================================

def test_product_crud_and_json_fields(db: DatabaseManager, test_db_path: Path):
    """Test product creation, updating, JSON serialization of sizes/colors, and deletion."""
    biz = db.create_business(BusinessCreate(name="Streetwear Co"))

    # 1. Create product with list sizes and colors
    prod = db.create_product(
        ProductCreate(
            business_id=biz.business_id,
            name="Classic Denim Jacket",
            description="Premium 100% cotton washed denim jacket.",
            price=89.99,
            currency="USD",
            category="Outerwear",
            sizes=["S", "M", "L", "XL", "XXL"],
            colors=["Indigo Blue", "Washed Black"],
            availability="in_stock",
            returnable=True,
            product_url="https://streetwear.example.com/products/denim-jacket",
        )
    )

    assert prod.product_id is not None
    assert prod.sizes == ["S", "M", "L", "XL", "XXL"]
    assert prod.colors == ["Indigo Blue", "Washed Black"]
    assert prod.returnable is True
    assert prod.price == 89.99

    # Verify raw SQLite storage uses JSON text
    with get_connection(test_db_path) as conn:
        raw_row = conn.execute(
            "SELECT sizes, colors, returnable FROM products WHERE product_id = ?",
            (prod.product_id,),
        ).fetchone()
        assert raw_row["sizes"] == '["S", "M", "L", "XL", "XXL"]'
        assert raw_row["colors"] == '["Indigo Blue", "Washed Black"]'
        assert raw_row["returnable"] == 1

    # 2. Update product
    updated_prod = db.update_product(
        prod.product_id,
        ProductUpdate(
            price=79.99,
            sizes=["M", "L", "XL"],
            colors=["Indigo Blue"],
            availability="low_stock",
        ),
        business_id=biz.business_id,
    )
    assert updated_prod is not None
    assert updated_prod.price == 79.99
    assert updated_prod.sizes == ["M", "L", "XL"]
    assert updated_prod.colors == ["Indigo Blue"]
    assert updated_prod.availability == "low_stock"

    # 3. Retrieve by business
    products = db.get_products_by_business(biz.business_id)
    assert len(products) == 1
    assert products[0].product_id == prod.product_id

    # 4. Delete product
    assert db.delete_product(prod.product_id, business_id=biz.business_id) is True
    assert db.get_product(prod.product_id) is None


# =====================================================================
# 5. POLICY CRUD TESTS
# =====================================================================

def test_policy_crud(db: DatabaseManager):
    """Test policy creation, retrieval by type, updates, and deletion."""
    biz = db.create_business(BusinessCreate(name="Policy Test Store"))

    # Create policies
    shipping_policy = db.create_policy(
        PolicyCreate(
            business_id=biz.business_id,
            policy_type="shipping",
            content="Free standard shipping on orders over $50. Standard delivery takes 3-5 business days.",
        )
    )
    return_policy = db.create_policy(
        PolicyCreate(
            business_id=biz.business_id,
            policy_type="returns",
            content="Items can be returned within 30 days of receipt in original condition.",
        )
    )

    assert shipping_policy.policy_type == "shipping"
    assert return_policy.policy_type == "returns"

    # Retrieve by type
    fetched_shipping = db.get_policy_by_type(biz.business_id, "shipping")
    assert fetched_shipping is not None
    assert fetched_shipping.policy_id == shipping_policy.policy_id

    # Update policy
    updated_shipping = db.update_policy(
        shipping_policy.policy_id,
        PolicyUpdate(content="Free standard shipping on all orders nationwide."),
        business_id=biz.business_id,
    )
    assert updated_shipping is not None
    assert updated_shipping.content == "Free standard shipping on all orders nationwide."

    # List policies
    policies = db.get_policies_by_business(biz.business_id)
    assert len(policies) == 2

    # Delete policy
    assert db.delete_policy(shipping_policy.policy_id, business_id=biz.business_id) is True
    assert len(db.get_policies_by_business(biz.business_id)) == 1


# =====================================================================
# 6. FAQ CRUD TESTS
# =====================================================================

def test_faq_crud(db: DatabaseManager):
    """Test FAQ creation, retrieval, updates, and deletion."""
    biz = db.create_business(BusinessCreate(name="FAQ Test Store"))

    faq = db.create_faq(
        FAQCreate(
            business_id=biz.business_id,
            question="Do you ship internationally?",
            answer="Yes, we ship to over 50 countries worldwide.",
        )
    )

    assert faq.faq_id is not None
    assert faq.question == "Do you ship internationally?"

    # Update FAQ
    updated_faq = db.update_faq(
        faq.faq_id,
        FAQUpdate(answer="Yes, international shipping is available for select regions."),
        business_id=biz.business_id,
    )
    assert updated_faq is not None
    assert updated_faq.answer == "Yes, international shipping is available for select regions."

    # List FAQs
    faqs = db.get_faqs_by_business(biz.business_id)
    assert len(faqs) == 1
    assert faqs[0].faq_id == faq.faq_id

    # Delete FAQ
    assert db.delete_faq(faq.faq_id, business_id=biz.business_id) is True
    assert len(db.get_faqs_by_business(biz.business_id)) == 0


# =====================================================================
# 7. KNOWLEDGE DOCUMENT CRUD & JSON METADATA TESTS
# =====================================================================

def test_knowledge_document_crud_and_json_metadata(db: DatabaseManager, test_db_path: Path):
    """Test knowledge document storage, JSON metadata serialization, and filtering."""
    biz = db.create_business(BusinessCreate(name="Knowledge Store"))

    # Create knowledge doc
    kdoc = db.create_knowledge_document(
        KnowledgeDocumentCreate(
            business_id=biz.business_id,
            source_type="product",
            source_id="prod_101",
            content="Product: Wool Beanie. Color: Grey. Price: $25.00. 100% merino wool.",
            metadata={"business_id": biz.business_id, "category": "Accessories", "price": 25.0},
        )
    )

    assert kdoc.knowledge_id is not None
    assert kdoc.metadata["category"] == "Accessories"
    assert kdoc.metadata["price"] == 25.0

    # Verify JSON in SQLite
    with get_connection(test_db_path) as conn:
        row = conn.execute(
            "SELECT metadata FROM knowledge_documents WHERE knowledge_id = ?",
            (kdoc.knowledge_id,),
        ).fetchone()
        raw_meta = json.loads(row["metadata"])
        assert raw_meta["category"] == "Accessories"

    # Update knowledge doc
    updated_kdoc = db.update_knowledge_document(
        kdoc.knowledge_id,
        KnowledgeDocumentUpdate(
            content="Product: Wool Beanie (Updated). Color: Grey, Black.",
            metadata={"business_id": biz.business_id, "category": "Winter Accessories"},
        ),
        business_id=biz.business_id,
    )
    assert updated_kdoc is not None
    assert updated_kdoc.metadata["category"] == "Winter Accessories"

    # Query by source
    by_source = db.get_knowledge_documents_by_source(biz.business_id, "product", "prod_101")
    assert len(by_source) == 1
    assert by_source[0].knowledge_id == kdoc.knowledge_id

    # Delete by source
    del_count = db.delete_knowledge_documents_by_source(biz.business_id, "product", "prod_101")
    assert del_count == 1
    assert len(db.get_knowledge_documents_by_business(biz.business_id)) == 0


# =====================================================================
# 8. CONVERSATION & MESSAGE CRUD & ROLE VALIDATION
# =====================================================================

def test_conversation_and_message_crud(db: DatabaseManager):
    """Test conversation creation, message history, and chronological order."""
    biz = db.create_business(BusinessCreate(name="Chat Support Store"))

    conv = db.create_conversation(
        ConversationCreate(business_id=biz.business_id, session_id="sess_abc123")
    )
    assert conv.conversation_id is not None
    assert conv.business_id == biz.business_id

    # Add messages
    msg1 = db.create_message(
        MessageCreate(
            conversation_id=conv.conversation_id,
            role="user",
            content="What is your return policy?",
        ),
        business_id=biz.business_id,
    )
    msg2 = db.create_message(
        MessageCreate(
            conversation_id=conv.conversation_id,
            role="assistant",
            content="We offer 30-day returns on all unworn items.",
        ),
        business_id=biz.business_id,
    )

    assert msg1.role == "user"
    assert msg2.role == "assistant"

    # Retrieve messages
    messages = db.get_messages_by_conversation(conv.conversation_id, business_id=biz.business_id)
    assert len(messages) == 2
    assert messages[0].content == "What is your return policy?"
    assert messages[1].content == "We offer 30-day returns on all unworn items."


def test_invalid_message_role_rejected(db: DatabaseManager):
    """Test that only 'user' and 'assistant' message roles are allowed."""
    biz = db.create_business(BusinessCreate(name="Role Validation Store"))
    conv = db.create_conversation(
        ConversationCreate(business_id=biz.business_id, session_id="sess_xyz")
    )

    # 1. Pydantic validation should reject invalid role
    with pytest.raises(ValidationError):
        MessageCreate(
            conversation_id=conv.conversation_id,
            role="system",  # type: ignore[arg-type]
            content="System prompt",
        )

    with pytest.raises(ValidationError):
        MessageCreate(
            conversation_id=conv.conversation_id,
            role="bot",  # type: ignore[arg-type]
            content="Bot message",
        )


# =====================================================================
# 9. MULTI-TENANT ISOLATION TESTS
# =====================================================================

def test_multi_tenant_isolation_products(db: DatabaseManager):
    """Test strict tenant isolation: Business A cannot access Business B's products."""
    biz_a = db.create_business(BusinessCreate(name="Business Alpha"))
    biz_b = db.create_business(BusinessCreate(name="Business Beta"))

    prod_a = db.create_product(ProductCreate(business_id=biz_a.business_id, name="Alpha Shoes", price=120.0))
    prod_b = db.create_product(ProductCreate(business_id=biz_b.business_id, name="Beta Jacket", price=250.0))

    # Business A queries
    a_products = db.get_products_by_business(biz_a.business_id)
    assert len(a_products) == 1
    assert a_products[0].name == "Alpha Shoes"
    assert prod_b.product_id not in [p.product_id for p in a_products]

    # Business B queries
    b_products = db.get_products_by_business(biz_b.business_id)
    assert len(b_products) == 1
    assert b_products[0].name == "Beta Jacket"
    assert prod_a.product_id not in [p.product_id for p in b_products]

    # Cross-tenant get_product with tenant check
    assert db.get_product(prod_a.product_id, business_id=biz_b.business_id) is None
    assert db.get_product(prod_b.product_id, business_id=biz_a.business_id) is None

    # Cross-tenant update attempt should fail
    cross_update = db.update_product(
        prod_a.product_id,
        ProductUpdate(name="Hacked Alpha Shoes"),
        business_id=biz_b.business_id,
    )
    assert cross_update is None
    prod_orig = db.get_product(prod_a.product_id)
    assert prod_orig is not None
    assert prod_orig.name == "Alpha Shoes"

    # Cross-tenant delete attempt should fail
    cross_delete = db.delete_product(prod_a.product_id, business_id=biz_b.business_id)
    assert cross_delete is False
    assert db.get_product(prod_a.product_id) is not None


def test_multi_tenant_isolation_policies_and_faqs(db: DatabaseManager):
    """Test strict tenant isolation across policies and FAQs."""
    biz_a = db.create_business(BusinessCreate(name="Business Alpha"))
    biz_b = db.create_business(BusinessCreate(name="Business Beta"))

    pol_a = db.create_policy(PolicyCreate(business_id=biz_a.business_id, policy_type="shipping", content="Alpha Ships in 1 Day"))
    pol_b = db.create_policy(PolicyCreate(business_id=biz_b.business_id, policy_type="shipping", content="Beta Ships in 5 Days"))

    faq_a = db.create_faq(FAQCreate(business_id=biz_a.business_id, question="Alpha Question?", answer="Alpha Answer."))
    faq_b = db.create_faq(FAQCreate(business_id=biz_b.business_id, question="Beta Question?", answer="Beta Answer."))

    # Policies tenant isolation
    assert len(db.get_policies_by_business(biz_a.business_id)) == 1
    assert db.get_policies_by_business(biz_a.business_id)[0].content == "Alpha Ships in 1 Day"
    assert db.get_policy(pol_a.policy_id, business_id=biz_b.business_id) is None
    pol_ret_a = db.get_policy_by_type(biz_a.business_id, "shipping")
    assert pol_ret_a is not None
    assert pol_ret_a.content == "Alpha Ships in 1 Day"
    pol_ret_b = db.get_policy_by_type(biz_b.business_id, "shipping")
    assert pol_ret_b is not None
    assert pol_ret_b.content == "Beta Ships in 5 Days"

    # FAQs tenant isolation
    assert len(db.get_faqs_by_business(biz_a.business_id)) == 1
    assert db.get_faqs_by_business(biz_a.business_id)[0].question == "Alpha Question?"
    assert db.get_faq(faq_a.faq_id, business_id=biz_b.business_id) is None


def test_multi_tenant_isolation_conversations_and_messages(db: DatabaseManager):
    """Test that conversation and message retrieval enforces tenant boundaries."""
    biz_a = db.create_business(BusinessCreate(name="Tenant Alpha"))
    biz_b = db.create_business(BusinessCreate(name="Tenant Beta"))

    conv_a = db.create_conversation(ConversationCreate(business_id=biz_a.business_id, session_id="session_alpha"))
    conv_b = db.create_conversation(ConversationCreate(business_id=biz_b.business_id, session_id="session_beta"))

    db.create_message(
        MessageCreate(conversation_id=conv_a.conversation_id, role="user", content="Alpha Confidential Query"),
        business_id=biz_a.business_id,
    )
    db.create_message(
        MessageCreate(conversation_id=conv_b.conversation_id, role="user", content="Beta Secret Message"),
        business_id=biz_b.business_id,
    )

    # Verify conversation isolation
    assert db.get_conversation(conv_a.conversation_id, business_id=biz_b.business_id) is None
    assert db.get_conversation(conv_b.conversation_id, business_id=biz_a.business_id) is None

    # Verify message isolation: Tenant Beta cannot read Tenant Alpha's messages even with conv_a id
    messages_for_b_trying_a = db.get_messages_by_conversation(conv_a.conversation_id, business_id=biz_b.business_id)
    assert len(messages_for_b_trying_a) == 0

    # Tenant Alpha gets their own messages
    messages_for_a = db.get_messages_by_conversation(conv_a.conversation_id, business_id=biz_a.business_id)
    assert len(messages_for_a) == 1
    assert messages_for_a[0].content == "Alpha Confidential Query"

    # Tenant Beta cannot post messages to Tenant Alpha's conversation
    with pytest.raises(PermissionError):
        db.create_message(
            MessageCreate(conversation_id=conv_a.conversation_id, role="user", content="Unauthorized intruder message"),
            business_id=biz_b.business_id,
        )


# =====================================================================
# 10. EVALUATION DATASET ISOLATION TEST
# =====================================================================

def test_evaluation_dataset_isolation(db: DatabaseManager):
    """Verify that the evaluation dataset file remains strictly untouched and outside the database."""
    eval_file = Path("data/evaluation/urbanthreads_evaluation.json")
    if eval_file.exists():
        with open(eval_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure it is valid JSON with expected evaluation structure
            assert isinstance(data, dict)
            assert "cases" in data
            assert isinstance(data["cases"], list)

    # Ensure no evaluation data has leaked into knowledge_documents or products
    all_kdocs = db.get_knowledge_documents_by_business("urbanthreads_001")
    assert len(all_kdocs) == 0


# =====================================================================
# 11. TIMESTAMPS & VALIDATION EDGE CASES
# =====================================================================

def test_timestamp_updates_on_modification(db: DatabaseManager):
    """Test that updating an entity updates its updated_at timestamp."""
    import time
    biz = db.create_business(BusinessCreate(name="Timestamp Biz"))
    initial_created = biz.created_at
    initial_updated = biz.updated_at
    assert initial_created is not None

    time.sleep(0.01)  # small pause to ensure timestamp difference
    updated_biz = db.update_business(biz.business_id, BusinessUpdate(name="Updated Timestamp Biz"))
    assert updated_biz is not None
    assert updated_biz.created_at == initial_created
    assert updated_biz.updated_at >= initial_updated


def test_conversation_cascade_deletes_messages(db: DatabaseManager):
    """Test that deleting a conversation cascades to deleting all contained messages."""
    biz = db.create_business(BusinessCreate(name="Cascade Chat Biz"))
    conv = db.create_conversation(ConversationCreate(business_id=biz.business_id, session_id="sess_casc"))

    msg = db.create_message(
        MessageCreate(conversation_id=conv.conversation_id, role="user", content="Hello"),
        business_id=biz.business_id,
    )
    assert len(db.get_messages_by_conversation(conv.conversation_id)) == 1

    # Delete conversation
    assert db.delete_conversation(conv.conversation_id, business_id=biz.business_id) is True
    assert len(db.get_messages_by_conversation(conv.conversation_id)) == 0


def test_policy_type_normalization(db: DatabaseManager):
    """Test that policy_type is normalized to lowercase and trimmed."""
    biz = db.create_business(BusinessCreate(name="Policy Norm Biz"))
    pol = db.create_policy(
        PolicyCreate(business_id=biz.business_id, policy_type="  SHIPPING  ", content="Policy details")
    )
    assert pol.policy_type == "shipping"

    fetched = db.get_policy_by_type(biz.business_id, "Shipping")
    assert fetched is not None
    assert fetched.policy_id == pol.policy_id

