"""Dashboard overview page for SupportBot AI."""

import streamlit as st

from app.components.common import get_current_business, render_header
from services.assistant_service import assistant_service
from services.faq_service import faq_service
from services.policy_service import policy_service
from services.product_service import product_service


def render_dashboard_page() -> None:
    """Render the dashboard overview for the active business."""
    render_header(
        "📊 Business Dashboard Overview",
        "Monitor your business profile, knowledge catalog, and AI assistant readiness.",
    )

    biz = get_current_business()
    if not biz:
        st.info("👋 Welcome to SupportBot AI!")
        st.write(
            "Get started by creating your business profile in **Business Setup** using the sidebar navigation."
        )
        return

    # Metrics overview row
    products = product_service.get_products_by_business(biz.business_id)
    policies = policy_service.get_policies_by_business(biz.business_id)
    faqs = faq_service.get_faqs_by_business(biz.business_id)
    asst = assistant_service.get_assistant_settings(biz.business_id)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="🛍️ Products", value=len(products))
    with col2:
        st.metric(label="📜 Policies", value=len(policies))
    with col3:
        st.metric(label="❓ FAQs", value=len(faqs))
    with col4:
        asst_status = "Configured" if asst else "Not Set"
        st.metric(label="🤖 AI Assistant", value=asst_status)

    st.markdown("---")

    # Business Information Card
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader(f"🏢 {biz.name}")
        if biz.description:
            st.write(f"*{biz.description}*")

        details_col1, details_col2 = st.columns(2)
        with details_col1:
            st.markdown(f"**Industry:** {biz.industry or 'N/A'}")
            st.markdown(f"**Location:** {biz.location or 'N/A'}")
            st.markdown(f"**Business ID:** `{biz.business_id}`")
        with details_col2:
            st.markdown(f"**Website:** {biz.website or 'N/A'}")
            st.markdown(f"**Email:** {biz.contact_email or 'N/A'}")
            st.markdown(f"**Phone:** {biz.contact_phone or 'N/A'}")

    with right_col:
        st.subheader("🤖 Assistant Profile")
        if asst:
            st.markdown(f"**Name:** {asst.assistant_name}")
            st.markdown(f"**Tone:** {asst.tone or 'Default'}")
            st.markdown(f"**Greeting:** *\"{asst.welcome_message or 'None'}\"*")
        else:
            st.warning("AI Assistant is not configured yet.")
            st.caption("Configure assistant name and tone under **AI Assistant Settings**.")

    st.markdown("---")

    # Setup progress / readiness summary
    st.subheader("📋 Knowledge Readiness Checklist")
    c1, c2, c3, c4 = st.columns(4)
    c1.checkbox("Business Profile", value=True, disabled=True)
    c2.checkbox("Products Added", value=len(products) > 0, disabled=True)
    c3.checkbox("Policies Configured", value=len(policies) > 0, disabled=True)
    c4.checkbox("Assistant Settings", value=asst is not None, disabled=True)
