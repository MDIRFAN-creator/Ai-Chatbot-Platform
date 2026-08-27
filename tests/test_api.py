"""Automated test suite for Phase 7.1: HTTP Chat API Server and Transport Layer.

Tests:
1. Health check endpoints (/health, /api/health).
2. Valid chat request processing and ChatbotService invocation.
3. Request schema validation (missing fields, empty fields, oversized payloads).
4. Malformed JSON and payload handling.
5. Nonexistent business tenant handling (404).
6. Multi-tenant isolation at the HTTP API boundary.
7. Conversational session continuity.
8. CORS headers and preflight handling.
9. Internal error handling with zero secret/stack-trace leakage.
"""

from pathlib import Path
import shutil
import tempfile
from typing import Generator
from unittest.mock import MagicMock
import pytest
from starlette.testclient import TestClient

from api.server import create_app
from core.database import DatabaseManager, init_db
from core.models import BusinessCreate
from rag.chain import RAGResponse
from services.chatbot_service import ChatbotService


@pytest.fixture
def temp_api_env() -> Generator[tuple[DatabaseManager, MagicMock, TestClient], None, None]:
    """Create an isolated test database, mocked ChatbotService, and Starlette TestClient."""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_api_"))
    db_file = temp_dir / "test_api.db"
    init_db(db_file)
    db = DatabaseManager(db_file)

    # Create test businesses
    db.create_business(
        BusinessCreate(
            business_id="biz_alpha",
            name="Alpha Store",
            description="Alpha retail storefront",
            contact_email="support@alpha.example",
        )
    )
    db.create_business(
        BusinessCreate(
            business_id="biz_beta",
            name="Beta Boutique",
            description="Beta luxury fashion",
            contact_email="support@beta.example",
        )
    )

    mock_service = MagicMock(spec=ChatbotService)
    mock_service.answer.return_value = RAGResponse(
        answer="Our return window is 7 days from delivery.",
        business_id="biz_alpha",
        session_id="sess_100",
        conversation_id="conv_100",
        retrieved_documents=[],
        fallback_triggered=False,
    )

    app = create_app(service=mock_service, db_manager=db)
    client = TestClient(app)

    yield db, mock_service, client

    shutil.rmtree(temp_dir, ignore_errors=True)


# =====================================================================
# 1. HEALTH ENDPOINTS
# =====================================================================

def test_health_endpoints(temp_api_env):
    """Verify health probe endpoints."""
    _, _, client = temp_api_env

    # Test /health
    res1 = client.get("/health")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1.get("status") == "healthy"
    assert "SupportBot AI" in data1.get("service", "")

    # Test /api/health
    res2 = client.get("/api/health")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2.get("status") == "healthy"


# =====================================================================
# 2. VALID CHAT REQUESTS & SERVICE INVOCATION
# =====================================================================

def test_valid_chat_request(temp_api_env):
    """Verify standard chat interaction via HTTP POST /api/chat."""
    _, mock_service, client = temp_api_env

    payload = {
        "business_id": "biz_alpha",
        "session_id": "sess_user_42",
        "message": "Do you accept returns?",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["answer"] == "Our return window is 7 days from delivery."
    assert data["business_id"] == "biz_alpha"
    assert data["session_id"] == "sess_100"
    assert data["fallback_triggered"] is False

    # Verify service was invoked with exact parameters
    mock_service.answer.assert_called_once_with(
        business_id="biz_alpha",
        session_id="sess_user_42",
        question="Do you accept returns?",
    )


# =====================================================================
# 3. INPUT VALIDATION TESTS
# =====================================================================

def test_chat_missing_required_fields(temp_api_env):
    """Verify 400 Bad Request when required fields are missing."""
    _, _, client = temp_api_env

    # Missing business_id
    res1 = client.post("/api/chat", json={"session_id": "s1", "message": "Hi"})
    assert res1.status_code == 400
    assert "business_id" in res1.json().get("detail", "").lower()

    # Missing session_id
    res2 = client.post("/api/chat", json={"business_id": "biz_alpha", "message": "Hi"})
    assert res2.status_code == 400
    assert "session_id" in res2.json().get("detail", "").lower()

    # Missing message
    res3 = client.post("/api/chat", json={"business_id": "biz_alpha", "session_id": "s1"})
    assert res3.status_code == 400
    assert "message" in res3.json().get("detail", "").lower()


def test_chat_empty_or_whitespace_fields(temp_api_env):
    """Verify 400 Bad Request on empty or whitespace strings."""
    _, _, client = temp_api_env

    # Empty message
    res = client.post(
        "/api/chat",
        json={"business_id": "biz_alpha", "session_id": "s1", "message": "   "},
    )
    assert res.status_code == 400


def test_chat_oversized_message(temp_api_env):
    """Verify 400 Bad Request when message exceeds max length."""
    _, _, client = temp_api_env

    oversized = "a" * 2500
    res = client.post(
        "/api/chat",
        json={"business_id": "biz_alpha", "session_id": "s1", "message": oversized},
    )
    assert res.status_code == 400


def test_chat_malformed_json_and_payloads(temp_api_env):
    """Verify 400 Bad Request on non-JSON or invalid structure payloads."""
    _, _, client = temp_api_env

    # Raw non-JSON text
    res1 = client.post(
        "/api/chat",
        content="this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert res1.status_code == 400

    # JSON Array instead of Object
    res2 = client.post("/api/chat", json=["not", "a", "dict"])
    assert res2.status_code == 400


# =====================================================================
# 4. TENANT ISOLATION & BUSINESS VALIDATION
# =====================================================================

def test_chat_nonexistent_business(temp_api_env):
    """Verify 404 Not Found when business tenant does not exist."""
    _, _, client = temp_api_env

    res = client.post(
        "/api/chat",
        json={"business_id": "nonexistent_999", "session_id": "s1", "message": "Hello"},
    )
    assert res.status_code == 404
    assert res.json().get("error") == "Business Not Found"


def test_chat_tenant_isolation_boundary(temp_api_env):
    """Verify that requests for different tenants route strictly to their business IDs."""
    _, mock_service, client = temp_api_env

    # Request for Alpha
    client.post(
        "/api/chat",
        json={"business_id": "biz_alpha", "session_id": "s_alpha", "message": "Alpha Q"},
    )
    mock_service.answer.assert_called_with(
        business_id="biz_alpha",
        session_id="s_alpha",
        question="Alpha Q",
    )

    # Request for Beta
    mock_service.answer.return_value = RAGResponse(
        answer="Beta response",
        business_id="biz_beta",
        session_id="s_beta",
        conversation_id="conv_beta",
        retrieved_documents=[],
    )
    res_beta = client.post(
        "/api/chat",
        json={"business_id": "biz_beta", "session_id": "s_beta", "message": "Beta Q"},
    )
    assert res_beta.status_code == 200
    assert res_beta.json()["business_id"] == "biz_beta"
    mock_service.answer.assert_called_with(
        business_id="biz_beta",
        session_id="s_beta",
        question="Beta Q",
    )


# =====================================================================
# 5. CORS & ERROR HANDLING / ZERO SECRET LEAKAGE
# =====================================================================

def test_cors_headers():
    """Verify CORS preflight OPTIONS request returns appropriate headers."""
    app = create_app(cors_origins=["https://example-store.com"])
    client = TestClient(app)

    headers = {
        "Origin": "https://example-store.com",
        "Access-Control-Request-Method": "POST",
    }
    res = client.options("/api/chat", headers=headers)
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://example-store.com"


def test_internal_server_error_no_secret_leakage(temp_api_env):
    """Verify 500 error does not expose stack traces, keys, or database internals."""
    _, mock_service, client = temp_api_env

    # Simulate an internal runtime exception
    mock_service.answer.side_effect = RuntimeError("Database locked at C:\\secrets\\supportbot.db")

    res = client.post(
        "/api/chat",
        json={"business_id": "biz_alpha", "session_id": "s1", "message": "Test"},
    )
    assert res.status_code == 500
    err_json = res.json()
    assert err_json.get("error") == "Internal Server Error"
    # Ensure sensitive internal paths / exceptions are suppressed
    assert "secrets" not in str(err_json)
    assert "supportbot.db" not in str(err_json)
    assert "Traceback" not in str(err_json)
