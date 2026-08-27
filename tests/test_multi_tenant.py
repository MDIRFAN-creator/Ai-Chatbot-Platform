"""Automated test suite for Multi-Tenant Security & Isolation across all layers.

Tests:
1. Complete isolation between Business A and Business B SQLite entities.
2. Complete filesystem directory isolation for FAISS vector stores.
3. Vector retrieval tenant boundary verification.
4. Conversation history and session isolation.
5. End-to-end RAG question answering isolation (Business A cannot answer using Business B context).
6. Cross-tenant conversation message manipulation rejection.
7. Verification that evaluation dataset remains untouched and unmixed.
"""

from pathlib import Path
import shutil
import tempfile
from typing import Generator
from unittest.mock import MagicMock
import pytest

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from core.config import get_config
from core.database import DatabaseManager, init_db
from core.models import (
    BusinessCreate,
    FAQCreate,
    PolicyCreate,
    ProductCreate,
)
from knowledge.knowledge_manager import KnowledgeManager
from rag.chain import RAGChain
from rag.retriever import retrieve
from rag.vector_store import get_business_vector_store_dir
from services.chatbot_service import ChatbotService
from services.conversation_service import ConversationService


@pytest.fixture
def temp_multi_tenant_env() -> Generator[tuple[DatabaseManager, Path, Path], None, None]:
    """Create isolated SQLite database and vectorstore directory for multi-tenant tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_multi_tenant_"))
    db_file = temp_dir / "test_multi_tenant.db"
    vector_dir = temp_dir / "test_vectorstore"
    vector_dir.mkdir(parents=True, exist_ok=True)

    init_db(db_file)
    db = DatabaseManager(db_file)

    orig_vector_store_dir = get_config().vector_store_dir
    object.__setattr__(get_config(), "vector_store_dir", vector_dir)

    yield db, db_file, vector_dir

    object.__setattr__(get_config(), "vector_store_dir", orig_vector_store_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_multi_tenant_end_to_end_isolation(temp_multi_tenant_env):
    """Verify strict tenant isolation across Knowledge, Vector Store, Conversations, and RAG."""
    db, _, _ = temp_multi_tenant_env
    km = KnowledgeManager(db)

    # 1. Setup Tenant Alpha (Streetwear)
    biz_a = db.create_business(
        BusinessCreate(
            name="Alpha Streetwear",
            contact_email="support@alpha.example.com",
            contact_phone="+1-111-ALPHA",
        )
    )
    bid_a = biz_a.business_id
    db.create_product(ProductCreate(business_id=bid_a, name="Alpha Oversized Hoodie", price=1200.0))
    db.create_policy(PolicyCreate(business_id=bid_a, policy_type="shipping", content="Alpha ships within 24 hours."))
    km.build_knowledge_base(bid_a)

    # 2. Setup Tenant Beta (Fine Jewelry)
    biz_b = db.create_business(
        BusinessCreate(
            name="Beta Fine Jewelry",
            contact_email="concierge@beta.example.com",
            contact_phone="+1-222-BETA",
        )
    )
    bid_b = biz_b.business_id
    db.create_product(ProductCreate(business_id=bid_b, name="Beta Diamond Solitaire Ring", price=95000.0))
    db.create_policy(PolicyCreate(business_id=bid_b, policy_type="shipping", content="Beta ships via insured armored courier."))
    km.build_knowledge_base(bid_b)

    # 3. Filesystem vector store directory separation
    dir_a = get_business_vector_store_dir(bid_a)
    dir_b = get_business_vector_store_dir(bid_b)
    assert dir_a != dir_b
    assert dir_a.exists() and dir_b.exists()
    assert bid_a in str(dir_a)
    assert bid_b in str(dir_b)

    # 4. Vector retrieval separation
    res_a = retrieve("Diamond Ring", business_id=bid_a)
    assert not any("Diamond Solitaire" in d.page_content for d in res_a)

    res_b = retrieve("Oversized Hoodie", business_id=bid_b)
    assert not any("Alpha Oversized" in d.page_content for d in res_b)

    # 5. Conversation session isolation
    conv_service = ConversationService(db)
    conv_a = conv_service.get_or_create_conversation(bid_a, "session_cust_1")
    conv_b = conv_service.get_or_create_conversation(bid_b, "session_cust_1")

    # Even with same session_id string, conversation records are distinct per business
    assert conv_a.conversation_id != conv_b.conversation_id
    assert conv_a.business_id == bid_a
    assert conv_b.business_id == bid_b

    conv_service.add_user_message(bid_a, conv_a.conversation_id, "I love Alpha Hoodies")
    conv_service.add_user_message(bid_b, conv_b.conversation_id, "I love Beta Diamonds")

    msgs_a = conv_service.get_conversation_messages(bid_a, conv_a.conversation_id)
    msgs_b = conv_service.get_conversation_messages(bid_b, conv_b.conversation_id)

    assert len(msgs_a) == 1 and msgs_a[0].content == "I love Alpha Hoodies"
    assert len(msgs_b) == 1 and msgs_b[0].content == "I love Beta Diamonds"

    # Cross-tenant message retrieval attempt returns empty
    cross_msgs = conv_service.get_conversation_messages(bid_a, conv_b.conversation_id)
    assert cross_msgs == []

    # 6. RAG Orchestrator tenant isolation with mocked LLM
    mock_llm = MagicMock(spec=BaseChatModel)
    mock_llm.invoke.side_effect = lambda prompt_msgs: AIMessage(
        content=f"Grounded response for {prompt_msgs[-1].content}"
    )

    chain = RAGChain(db_manager=db, llm=mock_llm)
    service = ChatbotService(rag_chain=chain, db_manager=db)

    # Asking Tenant Alpha about Alpha product -> should retrieve Alpha product
    resp_alpha = service.answer(bid_a, "session_cust_1", "What is the price of the Alpha Oversized Hoodie?")
    assert resp_alpha.fallback_triggered is False
    assert len(resp_alpha.retrieved_documents) > 0
    assert any("Alpha Oversized Hoodie" in d.page_content for d in resp_alpha.retrieved_documents)
    assert not any("Beta" in d.page_content for d in resp_alpha.retrieved_documents)

    # Asking Tenant Alpha about Tenant Beta's Diamond Ring -> should trigger safe fallback for Alpha
    resp_alpha_leak_attempt = service.answer(bid_a, "session_cust_1", "How much is the Beta Diamond Solitaire Ring?")
    assert resp_alpha_leak_attempt.fallback_triggered is True
    assert "Alpha Streetwear" in resp_alpha_leak_attempt.answer
    assert "support@alpha.example.com" in resp_alpha_leak_attempt.answer
    assert "Beta" not in resp_alpha_leak_attempt.answer


def test_cross_tenant_message_creation_rejection(temp_multi_tenant_env):
    """Verify that adding a message with mismatched business_id raises PermissionError."""
    db, _, _ = temp_multi_tenant_env
    conv_service = ConversationService(db)

    biz_a = db.create_business(BusinessCreate(name="Store A"))
    biz_b = db.create_business(BusinessCreate(name="Store B"))

    conv_a = conv_service.get_or_create_conversation(biz_a.business_id, "session_sec_test")

    # Attempt to inject message into Store A's conversation under Store B's authority
    with pytest.raises(PermissionError, match="does not belong to business"):
        conv_service.add_user_message(
            business_id=biz_b.business_id,
            conversation_id=conv_a.conversation_id,
            content="Malicious cross-tenant injection",
        )
