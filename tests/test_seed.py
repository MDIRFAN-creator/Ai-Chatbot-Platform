"""Automated test suite for Phase 8: Seed Data Automation Pipeline.

Tests:
1. JSON fixture parsing and structure validity.
2. Isolated database seeding of business, products, policies, and FAQs.
3. Idempotent re-seeding behavior.
4. Force re-seeding and record restoration.
5. Knowledge base generation during seeding.
"""

from pathlib import Path
import shutil
import tempfile
from typing import Generator
import pytest

from core.database import DatabaseManager, init_db
from core.models import BusinessUpdate
from data.seed.seed_data import load_fixture, seed_urbanthreads


@pytest.fixture
def temp_db() -> Generator[DatabaseManager, None, None]:
    """Create an isolated test database."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_seed_"))
    db_file = temp_dir / "test_seed.db"
    init_db(db_file)
    db = DatabaseManager(db_file)
    yield db
    shutil.rmtree(temp_dir, ignore_errors=True)


# =====================================================================
# 1. FIXTURE INTEGRITY
# =====================================================================

def test_load_all_fixtures():
    """Verify all 4 UrbanThreads JSON fixture files are valid and non-empty."""
    business_data = load_fixture("business.json")
    assert "business" in business_data
    assert "assistant_settings" in business_data
    assert business_data["business"]["business_id"] == "urbanthreads_001"

    products = load_fixture("products.json")
    assert isinstance(products, list)
    assert len(products) >= 5
    for p in products:
        assert "name" in p
        assert "price" in p

    policies = load_fixture("policies.json")
    assert isinstance(policies, list)
    assert len(policies) >= 4

    faqs = load_fixture("faqs.json")
    assert isinstance(faqs, list)
    assert len(faqs) >= 4


# =====================================================================
# 2. DATABASE SEEDING
# =====================================================================

def test_seed_urbanthreads_in_isolation(temp_db: DatabaseManager):
    """Verify seed_urbanthreads inserts all records into SQLite."""
    biz_id = seed_urbanthreads(db=temp_db, rebuild_knowledge=False, force=False)
    assert biz_id == "urbanthreads_001"

    # Verify business
    biz = temp_db.get_business("urbanthreads_001")
    assert biz is not None
    assert biz.name == "UrbanThreads"

    # Verify assistant settings
    settings = temp_db.get_assistant_settings("urbanthreads_001")
    assert settings is not None
    assert settings.assistant_name == "UrbanThreads Assistant"

    # Verify products
    products = temp_db.get_products_by_business("urbanthreads_001")
    assert len(products) == 6
    product_names = [p.name for p in products]
    assert "Oversized Black Hoodie" in product_names
    assert "Bomber Jacket" in product_names

    # Verify policies
    policies = temp_db.get_policies_by_business("urbanthreads_001")
    assert len(policies) == 5
    policy_types = [p.policy_type for p in policies]
    assert "shipping" in policy_types
    assert "returns" in policy_types

    # Verify FAQs
    faqs = temp_db.get_faqs_by_business("urbanthreads_001")
    assert len(faqs) == 5


# =====================================================================
# 3. IDEMPOTENCY & FORCE OVERWRITE
# =====================================================================

def test_seed_urbanthreads_idempotency(temp_db: DatabaseManager):
    """Verify running seed multiple times without force does not duplicate records."""
    seed_urbanthreads(db=temp_db, rebuild_knowledge=False, force=False)
    # Second run
    seed_urbanthreads(db=temp_db, rebuild_knowledge=False, force=False)

    products = temp_db.get_products_by_business("urbanthreads_001")
    assert len(products) == 6
    policies = temp_db.get_policies_by_business("urbanthreads_001")
    assert len(policies) == 5


def test_seed_urbanthreads_force_overwrite(temp_db: DatabaseManager):
    """Verify running seed with force=True deletes and recreates tenant records cleanly."""
    seed_urbanthreads(db=temp_db, rebuild_knowledge=False, force=False)

    # Modify an existing record in SQLite
    temp_db.update_business("urbanthreads_001", BusinessUpdate(name="Modified Store Name"))
    biz_mod = temp_db.get_business("urbanthreads_001")
    assert biz_mod is not None
    assert biz_mod.name == "Modified Store Name"

    # Force re-seed
    seed_urbanthreads(db=temp_db, rebuild_knowledge=False, force=True)
    biz_reseeded = temp_db.get_business("urbanthreads_001")
    assert biz_reseeded is not None
    assert biz_reseeded.name == "UrbanThreads"


# =====================================================================
# 4. KNOWLEDGE BASE GENERATION ON SEED
# =====================================================================

def test_seed_with_knowledge_base_building(temp_db: DatabaseManager):
    """Verify seed_urbanthreads builds normalized knowledge documents."""
    seed_urbanthreads(db=temp_db, rebuild_knowledge=True, force=True)

    docs = temp_db.get_knowledge_documents_by_business("urbanthreads_001")
    assert len(docs) > 0
    source_types = {d.source_type for d in docs}
    assert "business" in source_types
    assert "product" in source_types
    assert "policy" in source_types
    assert "faq" in source_types
