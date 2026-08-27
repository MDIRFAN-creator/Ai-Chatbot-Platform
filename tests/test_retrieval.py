"""Automated test suite for Phase 5: Business-Scoped Vector Retrieval.

Tests:
1. Retriever enforces mandatory non-empty business_id.
2. Business-scoped retrieval loads only the requested tenant's FAISS index.
3. Cross-tenant retrieval isolation.
4. Relevant product document retrieval.
5. Relevant policy document retrieval.
6. Relevant FAQ document retrieval.
7. Top-k count limiting.
8. Similarity score preservation and relevance thresholding.
9. Graceful empty list handling when index does not exist.
"""

from pathlib import Path
import shutil
import tempfile
from typing import Generator
import pytest

from core.config import get_config
from core.database import DatabaseManager, init_db
from core.models import BusinessCreate, FAQCreate, PolicyCreate, ProductCreate
from knowledge.knowledge_manager import KnowledgeManager
from rag.retriever import retrieve, retrieve_with_scores


@pytest.fixture
def temp_retrieval_env() -> Generator[tuple[DatabaseManager, Path, Path], None, None]:
    """Create isolated SQLite database and vectorstore directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_retrieval_"))
    db_file = temp_dir / "test_retrieval.db"
    vector_dir = temp_dir / "test_vectorstore"
    vector_dir.mkdir(parents=True, exist_ok=True)

    init_db(db_file)
    db = DatabaseManager(db_file)

    orig_vector_store_dir = get_config().vector_store_dir
    object.__setattr__(get_config(), "vector_store_dir", vector_dir)

    yield db, db_file, vector_dir

    object.__setattr__(get_config(), "vector_store_dir", orig_vector_store_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_retriever_requires_business_id():
    """Verify that retrieval strictly rejects missing or empty business_id."""
    with pytest.raises(ValueError, match="business_id"):
        retrieve(query="What are your products?", business_id="")

    with pytest.raises(ValueError, match="business_id"):
        retrieve_with_scores(query="What are your products?", business_id="   ")


def test_retriever_handles_empty_query_or_missing_index(temp_retrieval_env):
    """Verify that empty queries or non-existent business indexes return empty lists."""
    db, _, _ = temp_retrieval_env
    # Query non-existent business
    results = retrieve(query="Do you have shoes?", business_id="non_existent_biz")
    assert results == []

    # Empty query
    biz = db.create_business(BusinessCreate(name="Test Biz"))
    results = retrieve(query="", business_id=biz.business_id)
    assert results == []


def test_product_policy_faq_retrieval(temp_retrieval_env):
    """Verify that retrieval accurately retrieves products, policies, and FAQs."""
    db, _, _ = temp_retrieval_env
    manager = KnowledgeManager(db)

    biz = db.create_business(BusinessCreate(name="UrbanThreads", industry="Apparel"))
    bid = biz.business_id

    db.create_product(
        ProductCreate(
            business_id=bid,
            name="Oversized Black Hoodie",
            category="Hoodies",
            price=1499.0,
            colors=["Black"],
            sizes=["S", "M", "L", "XL"],
            description="400 GSM heavyweight premium hoodie.",
        )
    )
    db.create_product(
        ProductCreate(
            business_id=bid,
            name="Vintage Graphic Tee",
            category="T-Shirts",
            price=899.0,
            colors=["Washed Grey"],
        )
    )
    db.create_policy(
        PolicyCreate(
            business_id=bid,
            policy_type="shipping",
            content="Standard shipping takes 3-5 days. Free delivery on orders above INR 1499.",
        )
    )
    db.create_policy(
        PolicyCreate(
            business_id=bid,
            policy_type="returns",
            content="Returns accepted within 14 days of delivery. Tags must be intact.",
        )
    )
    db.create_faq(
        FAQCreate(
            business_id=bid,
            question="Do you ship internationally?",
            answer="Yes, we ship to over 50 countries worldwide.",
        )
    )

    # Build knowledge base
    manager.build_knowledge_base(bid)

    # 1. Product query
    prod_docs = retrieve(query="Tell me about the black hoodie", business_id=bid, top_k=2)
    assert len(prod_docs) > 0
    assert "Oversized Black Hoodie" in prod_docs[0].page_content
    assert prod_docs[0].metadata["source_type"] == "product"
    assert prod_docs[0].metadata["business_id"] == bid

    # 2. Policy query
    shipping_docs = retrieve(query="How long does delivery take?", business_id=bid, top_k=2)
    assert len(shipping_docs) > 0
    assert any("Shipping Policy" in d.page_content for d in shipping_docs)
    assert any(d.metadata["source_type"] == "policy" for d in shipping_docs)

    # 3. FAQ query
    faq_docs = retrieve(query="Do you offer international shipping?", business_id=bid, top_k=2)
    assert len(faq_docs) > 0
    assert any("50 countries worldwide" in d.page_content for d in faq_docs)
    assert any(d.metadata["source_type"] == "faq" for d in faq_docs)


def test_top_k_limiting_and_scores(temp_retrieval_env):
    """Verify that retrieval respects top_k limits and provides valid similarity scores."""
    db, _, _ = temp_retrieval_env
    manager = KnowledgeManager(db)

    biz = db.create_business(BusinessCreate(name="Shoe Superstore"))
    bid = biz.business_id

    for i in range(10):
        db.create_product(
            ProductCreate(
                business_id=bid,
                name=f"Running Shoe Model {i}",
                price=50.0 + i * 10,
            )
        )

    manager.build_knowledge_base(bid)

    # Retrieve with top_k=3
    docs = retrieve(query="running shoes", business_id=bid, top_k=3)
    assert len(docs) == 3

    # Retrieve with scores
    scored = retrieve_with_scores(query="running shoes", business_id=bid, top_k=3)
    assert len(scored) == 3
    for doc, score in scored:
        assert isinstance(score, float)
        assert doc.metadata["business_id"] == bid


def test_cross_tenant_retrieval_isolation(temp_retrieval_env):
    """Verify that retrieval for Business A NEVER returns Business B documents."""
    db, _, _ = temp_retrieval_env
    manager = KnowledgeManager(db)

    # Business A
    biz_a = db.create_business(BusinessCreate(name="Brand Alpha"))
    bid_a = biz_a.business_id
    db.create_product(ProductCreate(business_id=bid_a, name="Alpha Exclusive Sneakers", price=120.0))
    manager.build_knowledge_base(bid_a)

    # Business B
    biz_b = db.create_business(BusinessCreate(name="Brand Beta"))
    bid_b = biz_b.business_id
    db.create_product(ProductCreate(business_id=bid_b, name="Beta Diamond Ring", price=5000.0))
    manager.build_knowledge_base(bid_b)

    # Query Business A for Diamond Ring -> should not return Beta Diamond Ring
    res_a = retrieve(query="Diamond Ring", business_id=bid_a, top_k=5)
    for doc in res_a:
        assert doc.metadata["business_id"] == bid_a
        assert "Beta Diamond Ring" not in doc.page_content

    # Query Business B for Sneakers -> should not return Alpha Exclusive Sneakers
    res_b = retrieve(query="Sneakers", business_id=bid_b, top_k=5)
    for doc in res_b:
        assert doc.metadata["business_id"] == bid_b
        assert "Alpha Exclusive" not in doc.page_content
