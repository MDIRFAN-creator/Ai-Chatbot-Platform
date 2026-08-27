"""Streamlit dashboard pages for SupportBot AI."""

from app.pages.assistant_settings import render_assistant_settings_page
from app.pages.business_setup import render_business_setup_page
from app.pages.chatbot import render_chatbot_page
from app.pages.dashboard import render_dashboard_page
from app.pages.embed import render_embed_page
from app.pages.evaluation import render_evaluation_page
from app.pages.faqs import render_faqs_page
from app.pages.knowledge_base import render_knowledge_base_page
from app.pages.policies import render_policies_page
from app.pages.products import render_products_page

__all__ = [
    "render_dashboard_page",
    "render_business_setup_page",
    "render_products_page",
    "render_policies_page",
    "render_faqs_page",
    "render_assistant_settings_page",
    "render_knowledge_base_page",
    "render_chatbot_page",
    "render_evaluation_page",
    "render_embed_page",
]
