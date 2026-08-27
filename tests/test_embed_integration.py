"""Automated test suite for Phase 9: Merchant Onboarding & Production-Grade JavaScript Embed Integration.

Tests:
1. Starlette static file serving for /widget/embed.js and /widget/test_page.html.
2. Embed JavaScript attribute parsing and alias handling (data-api-base, data-color, data-disabled).
3. Database persistence of widget configuration via AssistantSettings.
4. User-friendly error message mappings in client script.
5. Multi-tenant API chat integration with CORS headers.
"""

from pathlib import Path
import re
import pytest
from starlette.testclient import TestClient

from api.server import app, create_app
from core.database import DatabaseManager, init_db
from core.models import AssistantSettingsCreate, AssistantSettingsUpdate, BusinessCreate


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create a Starlette TestClient with an isolated test database."""
    db_file = tmp_path / "test_embed_api.db"
    init_db(db_file)
    db = DatabaseManager(db_file)
    db.create_business(
        BusinessCreate(business_id="urbanthreads_001", name="UrbanThreads")
    )
    test_app = create_app(db_manager=db)
    return TestClient(test_app)


# =====================================================================
# 1. STATIC FILE SERVING TESTS
# =====================================================================

def test_static_widget_serving_via_api(client: TestClient):
    """Verify that Starlette serves /widget/embed.js and /widget/test_page.html."""
    # Test embed.js serving
    res = client.get("/widget/embed.js")
    assert res.status_code == 200
    assert "SupportBot AI" in res.text
    assert "function" in res.text

    # Test test_page.html serving
    res_page = client.get("/widget/test_page.html")
    assert res_page.status_code == 200
    assert "UrbanThreads" in res_page.text
    assert "data-business-id" in res_page.text


# =====================================================================
# 2. JAVASCRIPT ATTRIBUTE ALIASES & PARSING
# =====================================================================

def test_widget_attribute_aliases_and_disabled():
    """Verify embed.js contains support for attribute aliases and disabled flag."""
    embed_js_path = Path(__file__).resolve().parent.parent / "widget" / "embed.js"
    assert embed_js_path.exists()
    content = embed_js_path.read_text(encoding="utf-8")

    # Verify alias support
    assert "data-api-base" in content
    assert "data-color" in content
    assert "data-name" in content
    assert "data-disabled" in content
    assert "data-enabled" in content

    # Verify duplicate initialization guard
    assert "__SupportBotWidgetInitialized" in content

    # Verify native textContent XSS protection
    assert ".textContent =" in content


# =====================================================================
# 3. ERROR HANDLING IN WIDGET
# =====================================================================

def test_widget_user_facing_error_handling():
    """Verify embed.js maps specific HTTP status codes to friendly user messages."""
    embed_js_path = Path(__file__).resolve().parent.parent / "widget" / "embed.js"
    content = embed_js_path.read_text(encoding="utf-8")

    # 404 tenant check
    assert "response.status === 404" in content
    # 400 validation check
    assert "response.status === 400" in content
    # Offline / network fallback
    assert "unable to connect" in content.lower()


# =====================================================================
# 4. ASSISTANT SETTINGS PERSISTENCE
# =====================================================================

def test_assistant_settings_persistence_for_widget(tmp_path: Path):
    """Verify that widget customization persists correctly in SQLite database."""
    db_path = tmp_path / "test_widget_db.db"
    init_db(db_path)
    db = DatabaseManager(db_path)

    # 1. Create Business
    biz = db.create_business(
        BusinessCreate(business_id="test_merchant_01", name="Aura Boutique")
    )
    assert biz.business_id == "test_merchant_01"

    # 2. Create Initial Settings
    settings = db.create_or_update_assistant_settings(
        AssistantSettingsCreate(
            business_id="test_merchant_01",
            assistant_name="Aura Stylist",
            tone="chic and polite",
            welcome_message="Bonjour! How can I help you style today?",
        )
    )
    assert settings.assistant_name == "Aura Stylist"

    # 3. Update Settings via Widget Configuration
    updated = db.create_or_update_assistant_settings(
        AssistantSettingsUpdate(
            assistant_name="Aura VIP Assistant",
            tone="luxury and enthusiastic",
            welcome_message="Welcome to Aura Boutique VIP Lounge!",
        ),
        business_id="test_merchant_01",
    )
    assert updated.assistant_name == "Aura VIP Assistant"
    assert updated.welcome_message == "Welcome to Aura Boutique VIP Lounge!"


# =====================================================================
# 5. CORS CONFIGURATION
# =====================================================================

def test_cors_origin_configuration():
    """Verify Starlette app enforces explicit allowed origins."""
    custom_app = create_app(cors_origins=["https://merchant-store.example.com"])
    custom_client = TestClient(custom_app)

    # Allowed origin
    res = custom_client.options(
        "/api/chat",
        headers={
            "Origin": "https://merchant-store.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("access-control-allow-origin") == "https://merchant-store.example.com"
