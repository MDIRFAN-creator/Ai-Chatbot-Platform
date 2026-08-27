"""Streamlit UI integration tests using Streamlit AppTest framework (Phase 3)."""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app_runner():
    """Create an AppTest instance for app/main.py with 15s timeout."""
    entrypoint = Path(__file__).resolve().parent.parent / "app" / "main.py"
    return AppTest.from_file(str(entrypoint), default_timeout=15)


def test_streamlit_app_loads(app_runner: AppTest):
    """Test that main Streamlit application loads without errors."""
    app_runner.run()
    assert not app_runner.exception
    assert len(app_runner.sidebar.title) >= 1
    assert "SupportBot AI" in app_runner.sidebar.title[0].value


def test_streamlit_navigation_pages(app_runner: AppTest):
    """Test navigating through each Phase 3 dashboard section."""
    app_runner.run()
    assert not app_runner.exception

    nav_options = [
        "📊 Dashboard Overview",
        "🏢 Business Setup",
        "🛍️ Products",
        "📜 Policies",
        "❓ FAQs",
        "🤖 AI Assistant Settings",
        "📚 Knowledge Base (Phase 4)",
        "💬 Chatbot Preview (Phase 5)",
        "🧪 Evaluation (Phase 6)",
        "🔌 Embed Widget (Phase 7)",
    ]

    for nav_item in nav_options:
        app_runner.sidebar.radio(key="main_navigation").set_value(nav_item).run()
        assert not app_runner.exception
