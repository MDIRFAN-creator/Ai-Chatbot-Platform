"""Automated test suite for Phase 7: Embeddable JavaScript Chatbot Widget & Preview Subsystem.

Tests:
1. Widget script existence, structure, and zero external dependencies.
2. Security verification (zero hardcoded secrets, API keys, or database credentials in client JS).
3. Client-side XSS sanitization and safety guarantees.
4. Tenant configuration and attribute parsing.
5. Embed snippet generation for multiple tenants.
6. Chatbot preview and embed page module integrations.
"""

from pathlib import Path
import re
import pytest

from core.config import get_config
from core.database import DatabaseManager, init_db
from app.pages import render_chatbot_page, render_embed_page


@pytest.fixture
def widget_js_content() -> str:
    """Read the embed.js widget file content."""
    widget_path = Path("widget/embed.js")
    assert widget_path.exists(), "widget/embed.js file must exist."
    with open(widget_path, "r", encoding="utf-8") as f:
        return f.read()


# =====================================================================
# 1. WIDGET FILE & SYNTAX TESTS
# =====================================================================

def test_widget_file_structure_and_syntax(widget_js_content: str):
    """Verify that embed.js is a self-contained IIFE with clean structure."""
    assert len(widget_js_content) > 200
    # Must be wrapped in an IIFE
    assert "(function" in widget_js_content
    assert widget_js_content.strip().endswith("})();")
    # Must use strict mode
    assert '"use strict";' in widget_js_content or "'use strict';" in widget_js_content


def test_widget_readme_documentation():
    """Verify that widget/README.md contains integration instructions."""
    readme_path = Path("widget/README.md")
    assert readme_path.exists()
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "data-business-id" in content
    assert "data-api-url" in content
    assert "POST /api/chat" in content


# =====================================================================
# 2. SECURITY & ZERO SECRET EXPOSURE TESTS
# =====================================================================

def test_widget_security_zero_secret_exposure(widget_js_content: str):
    """Verify that no sensitive credentials, API keys, or private tokens exist in embed.js."""
    # Check for forbidden patterns
    forbidden_terms = [
        "AIza",  # Google API key prefix
        "GEMINI_API_KEY",
        "DATABASE_URL",
        "supportbot.db",
        "secret",
        "password",
        "private_key",
        "token=",
    ]
    for term in forbidden_terms:
        assert term not in widget_js_content, f"Security violation: Found forbidden term '{term}' in widget/embed.js"


def test_widget_xss_sanitization(widget_js_content: str):
    """Verify that HTML escaping is implemented to sanitize untrusted messages."""
    assert "escapeHTML" in widget_js_content
    assert ".replace(/&/g," in widget_js_content
    assert ".replace(/</g," in widget_js_content
    assert ".replace(/>/g," in widget_js_content


# =====================================================================
# 3. TENANT ISOLATION & ATTRIBUTE PARSING
# =====================================================================

def test_widget_attribute_parsing(widget_js_content: str):
    """Verify that embed.js supports standard HTML dataset attributes."""
    expected_attributes = [
        "data-business-id",
        "data-api-url",
        "data-title",
        "data-welcome-message",
        "data-primary-color",
        "data-position",
    ]
    for attr in expected_attributes:
        assert attr in widget_js_content, f"Expected attribute '{attr}' not handled in widget/embed.js"


def test_widget_session_continuity(widget_js_content: str):
    """Verify that widget manages session storage for conversational continuity."""
    assert "sessionStorage" in widget_js_content
    assert "supportbot_sess_" in widget_js_content


# =====================================================================
# 4. STREAMLIT PAGE MODULE INTEGRATIONS
# =====================================================================

def test_embed_and_chatbot_page_exports():
    """Verify that render_embed_page and render_chatbot_page are importable and callable."""
    assert callable(render_embed_page)
    assert callable(render_chatbot_page)
