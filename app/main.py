"""Main entry point for SupportBot AI Streamlit Application."""

from pathlib import Path
import sys

# Ensure repository root is in Python path for direct script execution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from app.components.common import render_sidebar_business_selector
from app.pages import (
    render_assistant_settings_page,
    render_business_setup_page,
    render_chatbot_page,
    render_dashboard_page,
    render_embed_page,
    render_evaluation_page,
    render_faqs_page,
    render_knowledge_base_page,
    render_policies_page,
    render_products_page,
)
from core.database import init_db


def setup_app() -> None:
    """Initialize database and Streamlit page configuration."""
    st.set_page_config(
        page_title="SupportBot AI — Dashboard",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # Ensure database tables exist
    init_db()


def main() -> None:
    """Main application navigation router."""
    setup_app()

    # Sidebar branding
    st.sidebar.title("🤖 SupportBot AI")
    st.sidebar.caption("AI Customer Support SaaS Platform (V1)")
    st.sidebar.markdown("---")

    # Business context selector in sidebar
    active_biz = render_sidebar_business_selector()

    # Navigation menu
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

    selected_nav = st.sidebar.radio(
        "Navigation",
        options=nav_options,
        index=0,
        key="main_navigation",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("SupportBot AI V1 • SQLite + Streamlit")

    # Route to selected page
    if selected_nav == "📊 Dashboard Overview":
        render_dashboard_page()
    elif selected_nav == "🏢 Business Setup":
        render_business_setup_page()
    elif selected_nav == "🛍️ Products":
        render_products_page()
    elif selected_nav == "📜 Policies":
        render_policies_page()
    elif selected_nav == "❓ FAQs":
        render_faqs_page()
    elif selected_nav == "🤖 AI Assistant Settings":
        render_assistant_settings_page()
    elif selected_nav.startswith("📚 Knowledge Base"):
        render_knowledge_base_page()
    elif selected_nav.startswith("💬 Chatbot Preview"):
        render_chatbot_page()
    elif selected_nav.startswith("🧪 Evaluation"):
        render_evaluation_page()
    elif selected_nav.startswith("🔌 Embed Widget"):
        render_embed_page()


if __name__ == "__main__":
    main()
