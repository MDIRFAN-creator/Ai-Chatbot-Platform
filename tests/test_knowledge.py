"""Comprehensive automated test suite for Phase 4: Knowledge Base Pipeline & FAISS Vector Store.

Tests:
1. Metadata creation, validation, and serialization.
2. Business document normalization.
3. Product document normalization (atomic, all attributes).
4. Policy document normalization and length-aware chunking.
5. FAQ document normalization (atomic Q&A).
6. DocumentLoader tenant-scoped data retrieval.
7. Local Hugging Face embeddings model initialization & 384 dimension verification.
8. Business-scoped FAISS vector store creation, persistence, reload, and deletion.
9. SQLite knowledge_documents persistence.
10. KnowledgeManager end-to-end build pipeline.
11. Multi-tenant isolation (Business A vs Business B documents & index directories).
12. Stale data purge on regeneration and source record updates/deletions.
13. Evaluation dataset isolation (urbanthreads_evaluation.json is untouched & not indexed).
"""

import json
from pathlib import Path
import shutil
import tempfile
from typing import Generator
import pytest

from core.config import AppConfig, get_config
from core.database import DatabaseManager, init_db
from core.models import (
    BusinessCreate,
    FAQCreate,
    KnowledgeDocumentCreate,
    PolicyCreate,
    ProductCreate,
    ProductUpdate,
)
from knowledge.document_builder import (
    build_all_documents,
    build_business_document,
    build_catalog_document,
    build_faq_document,
    build_policy_documents,
    build_product_document,
)
from knowledge.document_loader import DocumentLoader
from knowledge.knowledge_manager import KnowledgeManager
from knowledge.metadata import (
    VALID_SOURCE_TYPES,
    create_document_metadata,
    validate_document_metadata,
)
from rag.embeddings import get_embedding_dimension, get_embedding_model
from rag.vector_store import (
    create_or_replace_index,
    delete_index,
    get_business_vector_store_dir,
    index_exists,
    load_index,
)
from services.knowledge_service import KnowledgeService


@pytest.fixture
def temp_env() -> Generator[tuple[DatabaseManager, Path, Path], None, None]:
    """Create an isolated temporary SQLite database and vectorstore directory for tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_phase4_"))
    db_file = temp_dir / "test_supportbot.db"
    vector_dir = temp_dir / "test_vectorstore"
    vector_dir.mkdir(parents=True, exist_ok=True)

    init_db(db_file)
    db = DatabaseManager(db_file)

    # Monkey-patch config vector_store_dir for test isolation
    orig_vector_store_dir = get_config().vector_store_dir
    object.__setattr__(get_config(), "vector_store_dir", vector_dir)

    yield db, db_file, vector_dir

    # Cleanup
    object.__setattr__(get_config(), "vector_store_dir", orig_vector_store_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


# =====================================================================
# 1. METADATA TESTS
# =====================================================================

def test_metadata_validation_success():
    """Test valid metadata creation and verification."""
    meta = create_document_metadata(
        business_id="biz_001",
        source_type="product",
        source_id="prod_123",
        category="hoodies",
        price=1499.0,
    )
    assert meta["business_id"] == "biz_001"
    assert meta["source_type"] == "product"
    assert meta["source_id"] == "prod_123"
    assert meta["category"] == "hoodies"
    assert meta["price"] == 1499.0


def test_metadata_validation_failures():
    """Test that missing mandatory fields or invalid source types raise ValueError."""
    with pytest.raises(ValueError, match="business_id"):
        create_document_metadata(business_id="", source_type="product", source_id="p1")

    with pytest.raises(ValueError, match="source_type"):
        create_document_metadata(business_id="b1", source_type="invalid_type", source_id="p1")

    with pytest.raises(ValueError, match="source_id"):
        create_document_metadata(business_id="b1", source_type="faq", source_id="")

    with pytest.raises(ValueError, match="dict"):
        validate_document_metadata("not a dict")  # type: ignore


# =====================================================================
# 2. DOCUMENT BUILDER TESTS
# =====================================================================

def test_business_document_builder(temp_env):
    """Test business document formatting and metadata."""
    db, _, _ = temp_env
    biz = db.create_business(
        BusinessCreate(
            name="UrbanThreads",
            description="Streetwear brand",
            industry="Apparel",
            website="https://urbanthreads.example.com",
            contact_email="support@urbanthreads.example.com",
            contact_phone="+1-800-URBAN",
            location="New York, NY",
        )
    )

    doc = build_business_document(biz)
    assert "Business Name: UrbanThreads" in doc.page_content
    assert "Streetwear brand" in doc.page_content
    assert "Apparel" in doc.page_content
    assert "https://urbanthreads.example.com" in doc.page_content
    assert "support@urbanthreads.example.com" in doc.page_content
    assert "+1-800-URBAN" in doc.page_content
    assert "New York, NY" in doc.page_content

    assert doc.metadata["business_id"] == biz.business_id
    assert doc.metadata["source_type"] == "business"
    assert doc.metadata["source_id"] == biz.business_id


def test_product_document_builder(temp_env):
    """Test product document formatting (atomic document, all attributes)."""
    db, _, _ = temp_env
    biz = db.create_business(BusinessCreate(name="Test Brand"))
    prod = db.create_product(
        ProductCreate(
            business_id=biz.business_id,
            name="Oversized Black Hoodie",
            category="Hoodies",
            price=1499.0,
            currency="INR",
            sizes=["S", "M", "L", "XL"],
            colors=["Black", "Charcoal"],
            availability="in_stock",
            returnable=True,
            product_url="https://test.example/hoodie",
            description="Premium 400 GSM heavyweight cotton hoodie.",
        )
    )

    doc = build_product_document(prod)
    assert "Product: Oversized Black Hoodie" in doc.page_content
    assert "Category: Hoodies" in doc.page_content
    assert "Price: INR 1499.00" in doc.page_content
    assert "Sizes: S, M, L, XL" in doc.page_content
    assert "Colors: Black, Charcoal" in doc.page_content
    assert "Availability: In Stock" in doc.page_content
    assert "Returnable: Yes" in doc.page_content
    assert "https://test.example/hoodie" in doc.page_content
    assert "Premium 400 GSM" in doc.page_content

    assert doc.metadata["business_id"] == biz.business_id
    assert doc.metadata["source_type"] == "product"
    assert doc.metadata["source_id"] == prod.product_id
    assert doc.metadata["category"] == "Hoodies"
    assert doc.metadata["price"] == 1499.0
    assert doc.metadata["returnable"] is True


def test_policy_document_builder_short(temp_env):
    """Test short policy document is kept as a single unchunked document."""
    db, _, _ = temp_env
    biz = db.create_business(BusinessCreate(name="Test Brand"))
    policy = db.create_policy(
        PolicyCreate(
            business_id=biz.business_id,
            policy_type="shipping",
            content="Standard delivery takes 3-5 business days. Express shipping is 1-2 days.",
        )
    )

    docs = build_policy_documents(policy, chunk_size=500, chunk_overlap=50)
    assert len(docs) == 1
    assert "Policy Type: Shipping Policy" in docs[0].page_content
    assert "Standard delivery takes 3-5 business days" in docs[0].page_content
    assert docs[0].metadata["business_id"] == biz.business_id
    assert docs[0].metadata["source_type"] == "policy"
    assert docs[0].metadata["source_id"] == policy.policy_id
    assert docs[0].metadata["chunk_index"] == 0
    assert docs[0].metadata["total_chunks"] == 1


def test_policy_document_builder_long_chunking(temp_env):
    """Test length-aware chunking for long policies exceeding chunk_size."""
    db, _, _ = temp_env
    biz = db.create_business(BusinessCreate(name="Test Brand"))
    long_content = (
        "Section 1: Returns are accepted within 30 days of delivery. All items must be unworn. "
        "Section 2: Return shipping is free for store credit exchanges. Original tags must remain attached. "
        "Section 3: Refunds are credited to the original payment method within 5-7 banking days. "
        "Section 4: Final sale items and intimate apparel are non-returnable under any circumstances. "
        "Section 5: International orders require custom return label authorization from support."
    )
    policy = db.create_policy(
        PolicyCreate(
            business_id=biz.business_id,
            policy_type="returns",
            content=long_content,
        )
    )

    # Use a small chunk_size to enforce splitting
    docs = build_policy_documents(policy, chunk_size=150, chunk_overlap=20)
    assert len(docs) > 1

    for idx, doc in enumerate(docs):
        assert f"Part {idx + 1}/{len(docs)}" in doc.page_content
        assert doc.metadata["business_id"] == biz.business_id
        assert doc.metadata["source_type"] == "policy"
        assert doc.metadata["source_id"] == policy.policy_id
        assert doc.metadata["chunk_index"] == idx
        assert doc.metadata["total_chunks"] == len(docs)


def test_catalog_document_builder(temp_env):
    """Test product catalog summary document formatting and metadata."""
    db, _, _ = temp_env
    biz = db.create_business(BusinessCreate(name="UrbanThreads"))
    prod1 = db.create_product(
        ProductCreate(
            business_id=biz.business_id,
            name="Oversized Black Hoodie",
            category="Hoodies",
            price=1499.0,
            currency="INR",
            colors=["Black", "Charcoal"],
        )
    )
    prod2 = db.create_product(
        ProductCreate(
            business_id=biz.business_id,
            name="Bomber Jacket",
            category="Jackets",
            price=2499.0,
            currency="INR",
            colors=["Olive"],
        )
    )

    doc = build_catalog_document([prod1, prod2], business=biz)
    assert doc is not None
    assert "Product Catalog & Offerings: Products We Sell at UrbanThreads" in doc.page_content
    assert "Oversized Black Hoodie (Category: Hoodies) (Price: INR 1499.00) (Colors: Black, Charcoal)" in doc.page_content
    assert "Bomber Jacket (Category: Jackets) (Price: INR 2499.00) (Colors: Olive)" in doc.page_content
    assert doc.metadata["business_id"] == biz.business_id
    assert doc.metadata["source_type"] == "product"
    assert doc.metadata["source_id"] == f"{biz.business_id}_catalog"


def test_faq_document_builder(temp_env):
    """Test FAQ document formatting (atomic Q&A)."""
    db, _, _ = temp_env
    biz = db.create_business(BusinessCreate(name="Test Brand"))
    faq = db.create_faq(
        FAQCreate(
            business_id=biz.business_id,
            question="Is free shipping available?",
            answer="Yes, free shipping applies on orders above INR 1499.",
        )
    )

    doc = build_faq_document(faq)
    assert "Question:\nIs free shipping available?" in doc.page_content
    assert "Answer:\nYes, free shipping applies on orders above INR 1499." in doc.page_content
    assert doc.metadata["business_id"] == biz.business_id
    assert doc.metadata["source_type"] == "faq"
    assert doc.metadata["source_id"] == faq.faq_id


# =====================================================================
# 3. EMBEDDING & VECTOR STORE TESTS
# =====================================================================

def test_local_embeddings_dimension():
    """Verify local Hugging Face embedding model loads and outputs 384 dimensions."""
    model = get_embedding_model()
    dim = get_embedding_dimension(model)
    assert dim == 384

    probe_vector = model.embed_query("SupportBot AI Knowledge Pipeline")
    assert len(probe_vector) == 384
    assert isinstance(probe_vector[0], float)


def test_faiss_vector_store_persistence_and_reload(temp_env):
    """Test FAISS index creation, disk persistence, and reloading."""
    db, _, vector_dir = temp_env
    biz_id = "test_faiss_biz"

    docs = [
        build_faq_document(
            FAQCreate(
                business_id=biz_id,
                question="What is the warranty period?",
                answer="1 year limited warranty.",
            )
        )
    ]

    embeddings = get_embedding_model()

    # Index should not exist initially
    assert not index_exists(biz_id)

    # Create & persist index
    vs = create_or_replace_index(biz_id, docs, embeddings)
    assert vs is not None
    assert index_exists(biz_id)

    # Verify index directory exists inside vector_store_dir
    index_path = get_business_vector_store_dir(biz_id)
    assert index_path.is_dir()
    assert (index_path / "index.faiss").exists()
    assert (index_path / "index.pkl").exists()

    # Load persisted index
    loaded_vs = load_index(biz_id, embeddings)
    assert loaded_vs is not None
    assert len(getattr(loaded_vs.docstore, "_dict")) == 1

    # Delete index
    assert delete_index(biz_id) is True
    assert not index_exists(biz_id)


# =====================================================================
# 4. KNOWLEDGE MANAGER & SERVICE PIPELINE TESTS
# =====================================================================

def test_knowledge_manager_full_build(temp_env):
    """Test end-to-end knowledge base generation from SQLite to SQLite persistence and FAISS."""
    db, _, vector_dir = temp_env
    manager = KnowledgeManager(db)

    # Create business tenant and entities
    biz = db.create_business(BusinessCreate(name="Alpha Store", industry="Retail"))
    bid = biz.business_id

    db.create_product(ProductCreate(business_id=bid, name="Sneakers", price=79.99))
    db.create_product(ProductCreate(business_id=bid, name="Cap", price=19.99))
    db.create_policy(PolicyCreate(business_id=bid, policy_type="shipping", content="Fast shipping."))
    db.create_faq(FAQCreate(business_id=bid, question="Track order?", answer="Use tracking ID."))

    # Build knowledge base
    result = manager.build_knowledge_base(bid)

    assert result["business_id"] == bid
    assert result["status"] == "success"
    assert result["source_counts"]["business"] == 1
    assert result["source_counts"]["products"] == 2
    assert result["source_counts"]["policies"] == 1
    assert result["source_counts"]["faqs"] == 1
    assert result["normalized_documents_count"] == 6  # 1 biz + 1 catalog + 2 products + 1 policy + 1 faq
    assert result["faiss_index_ready"] is True

    # Verify SQLite knowledge_documents table was populated
    kdocs = db.get_knowledge_documents_by_business(bid)
    assert len(kdocs) == 6
    source_types = {kd.source_type for kd in kdocs}
    assert source_types == {"business", "product", "policy", "faq"}

    # Verify FAISS index was persisted
    assert index_exists(bid)
    embeddings = get_embedding_model()
    loaded_vs = load_index(bid, embeddings)
    assert loaded_vs is not None
    assert len(getattr(loaded_vs.docstore, "_dict")) == 6



def test_stale_data_purging_on_update_and_regeneration(temp_env):
    """Verify that updating/deleting structured SQLite data and regenerating removes stale knowledge."""
    db, _, _ = temp_env
    manager = KnowledgeManager(db)

    biz = db.create_business(BusinessCreate(name="Beta Store"))
    bid = biz.business_id

    prod = db.create_product(ProductCreate(business_id=bid, name="Graphic Tee", price=1000.0))
    manager.build_knowledge_base(bid)

    # Verify price in knowledge documents is 1000.00
    kdocs_v1 = db.get_knowledge_documents_by_business(bid)
    tee_docs_v1 = [d for d in kdocs_v1 if d.source_id == prod.product_id]
    assert len(tee_docs_v1) == 1
    assert "1000.00" in tee_docs_v1[0].content

    # Update product price in SQLite
    db.update_product(prod.product_id, ProductUpdate(price=2000.0), business_id=bid)

    # Regenerate knowledge base
    manager.build_knowledge_base(bid)

    # Verify stale 1000.00 is completely replaced by 2000.00
    kdocs_v2 = db.get_knowledge_documents_by_business(bid)
    tee_docs_v2 = [d for d in kdocs_v2 if d.source_id == prod.product_id]
    assert len(tee_docs_v2) == 1
    assert "2000.00" in tee_docs_v2[0].content
    assert "1000.00" not in tee_docs_v2[0].content

    # Now delete product and regenerate
    db.delete_product(prod.product_id, business_id=bid)
    manager.build_knowledge_base(bid)

    kdocs_v3 = db.get_knowledge_documents_by_business(bid)
    tee_docs_v3 = [d for d in kdocs_v3 if d.source_id == prod.product_id]
    assert len(tee_docs_v3) == 0


def test_multi_tenant_isolation(temp_env):
    """Test strict tenant isolation: Business A and Business B data & indexes are never mixed."""
    db, _, _ = temp_env
    service = KnowledgeService(db_manager=db)

    # Setup Business A
    biz_a = db.create_business(BusinessCreate(name="Tenant Alpha"))
    bid_a = biz_a.business_id
    db.create_product(ProductCreate(business_id=bid_a, name="Alpha Shoes", price=500.0))

    # Setup Business B
    biz_b = db.create_business(BusinessCreate(name="Tenant Beta"))
    bid_b = biz_b.business_id
    db.create_product(ProductCreate(business_id=bid_b, name="Beta Jacket", price=9000.0))

    # Build both knowledge bases
    res_a = service.build_knowledge_base(bid_a)
    res_b = service.build_knowledge_base(bid_b)

    assert res_a["faiss_index_ready"] is True
    assert res_b["faiss_index_ready"] is True

    # Check distinct vector store directories
    dir_a = get_business_vector_store_dir(bid_a)
    dir_b = get_business_vector_store_dir(bid_b)
    assert dir_a != dir_b
    assert dir_a.exists() and dir_b.exists()

    # Verify SQLite documents isolation
    kdocs_a = service.get_knowledge_documents(bid_a)
    kdocs_b = service.get_knowledge_documents(bid_b)

    for doc in kdocs_a:
        assert doc.business_id == bid_a
        assert "Beta" not in doc.content

    for doc in kdocs_b:
        assert doc.business_id == bid_b
        assert "Alpha" not in doc.content

    # Verify loaded FAISS index isolation
    embeddings = get_embedding_model()
    vs_a = load_index(bid_a, embeddings)
    vs_b = load_index(bid_b, embeddings)

    assert vs_a is not None and vs_b is not None
    for doc in getattr(vs_a.docstore, "_dict", {}).values():
        assert doc.metadata["business_id"] == bid_a
    for doc in getattr(vs_b.docstore, "_dict", {}).values():
        assert doc.metadata["business_id"] == bid_b


def test_evaluation_dataset_isolation(temp_env):
    """Ensure data/evaluation/urbanthreads_evaluation.json is never inserted into knowledge_documents or FAISS."""
    db, _, _ = temp_env
    manager = KnowledgeManager(db)

    eval_path = get_config().evaluation_dataset_path
    assert eval_path.exists(), "Evaluation dataset should exist in data/evaluation/"

    # Check that evaluation data contains questions
    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)
    assert len(eval_data) > 0

    cases = eval_data.get("cases", []) if isinstance(eval_data, dict) else eval_data
    assert len(cases) > 0

    # Build knowledge base for a test business
    biz = db.create_business(BusinessCreate(name="Test Tenant"))
    db.create_product(ProductCreate(business_id=biz.business_id, name="Sample Shirt", price=29.99))
    manager.build_knowledge_base(biz.business_id)

    # Inspect persisted knowledge documents
    kdocs = db.get_knowledge_documents_by_business(biz.business_id)
    persisted_contents = " ".join([kd.content for kd in kdocs])

    # Ensure evaluation-specific test questions/expected answers are not present
    for sample_eval in cases[:5]:
        sample_q = sample_eval.get("question", "")
        if sample_q:
            assert sample_q not in persisted_contents
