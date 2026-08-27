"""Reusable UI components and business context management for Streamlit dashboard."""

from typing import List, Optional
import streamlit as st

from core.models import Business
from services.business_service import business_service


def render_header(title: str, subtitle: Optional[str] = None) -> None:
    """Render a consistent branded page header."""
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.divider()


def init_session_state() -> None:
    """Initialize application session state variables."""
    if "business_id" not in st.session_state:
        st.session_state["business_id"] = None


def render_sidebar_business_selector() -> Optional[Business]:
    """Render the sidebar business selector and sync with session state."""
    init_session_state()

    st.sidebar.markdown("### 🏢 Business Context")
    businesses = business_service.list_businesses()

    if not businesses:
        st.sidebar.info("No businesses found. Please create a business in **Business Setup** to get started.")
        st.session_state["business_id"] = None
        return None

    # Map options
    biz_map = {b.business_id: f"{b.name} ({b.business_id})" for b in businesses}
    biz_ids = list(biz_map.keys())

    # Find current index
    current_id = st.session_state.get("business_id")
    current_index = biz_ids.index(current_id) if current_id is not None and current_id in biz_ids else 0

    selected_id = st.sidebar.selectbox(
        "Active Business Tenant:",
        options=biz_ids,
        index=current_index,
        format_func=lambda bid: biz_map.get(bid, bid),
        key="sidebar_biz_selector",
    )

    st.session_state["business_id"] = selected_id
    current_biz = business_service.get_business(selected_id)

    if current_biz:
        st.sidebar.caption(f"**Active:** {current_biz.name} | *{current_biz.industry or 'General'}*")

    st.sidebar.divider()
    return current_biz


def get_current_business() -> Optional[Business]:
    """Retrieve the currently selected business object from session state."""
    init_session_state()
    biz_id = st.session_state.get("business_id")
    if not biz_id:
        return None
    return business_service.get_business(biz_id)


def require_business_context() -> Optional[Business]:
    """Ensure a business is selected; if not, show a guided notice."""
    biz = get_current_business()
    if not biz:
        st.warning("⚠️ No active business selected.")
        st.info("Please navigate to **Business Setup** to create or select a business before managing data.")
        return None
    return biz
