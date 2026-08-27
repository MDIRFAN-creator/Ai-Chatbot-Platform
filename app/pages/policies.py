"""Business policy management page."""

from pydantic import ValidationError
import streamlit as st

from app.components.common import render_header, require_business_context
from app.components.forms import handle_validation_error
from core.models import PolicyCreate, PolicyUpdate
from services.policy_service import policy_service


def render_policies_page() -> None:
    """Render the business policies management interface."""
    render_header(
        "📜 Business Policies Management",
        "Configure your business rules (Shipping, Returns, Refunds) used by your AI assistant.",
    )

    biz = require_business_context()
    if not biz:
        return

    policies = policy_service.get_policies_by_business(biz.business_id)
    policy_map = {p.policy_type: p for p in policies}

    tabs = st.tabs(["🚚 Shipping", "🔄 Returns", "💰 Refunds", "➕ Add / Custom Policy", "📋 All Policies"])

    # 1. SHIPPING TAB
    with tabs[0]:
        st.subheader("🚚 Shipping Policy")
        shipping_pol = policy_map.get("shipping")
        current_content = shipping_pol.content if shipping_pol else ""

        with st.form("shipping_policy_form"):
            shipping_text = st.text_area(
                "Shipping Terms & Delivery Times",
                value=current_content,
                placeholder="e.g. Standard delivery takes 3-5 business days. Free shipping on orders over $50.",
                height=150,
            )
            save_shipping = st.form_submit_button("Save Shipping Policy", type="primary")

            if save_shipping:
                if not shipping_text.strip():
                    st.error("Policy content cannot be empty.")
                else:
                    try:
                        policy_service.create_or_update_policy(
                            business_id=biz.business_id,
                            policy_type="shipping",
                            content=shipping_text.strip(),
                        )
                        st.success("✅ Shipping policy saved successfully!")
                        st.rerun()
                    except ValidationError as e:
                        handle_validation_error(e)

    # 2. RETURNS TAB
    with tabs[1]:
        st.subheader("🔄 Return Policy")
        return_pol = policy_map.get("returns")
        current_return_content = return_pol.content if return_pol else ""

        with st.form("returns_policy_form"):
            return_text = st.text_area(
                "Return Windows & Conditions",
                value=current_return_content,
                placeholder="e.g. Items can be returned within 30 days of delivery in original condition with tags attached.",
                height=150,
            )
            save_return = st.form_submit_button("Save Return Policy", type="primary")

            if save_return:
                if not return_text.strip():
                    st.error("Policy content cannot be empty.")
                else:
                    try:
                        policy_service.create_or_update_policy(
                            business_id=biz.business_id,
                            policy_type="returns",
                            content=return_text.strip(),
                        )
                        st.success("✅ Return policy saved successfully!")
                        st.rerun()
                    except ValidationError as e:
                        handle_validation_error(e)

    # 3. REFUNDS TAB
    with tabs[2]:
        st.subheader("💰 Refund Policy")
        refund_pol = policy_map.get("refunds")
        current_refund_content = refund_pol.content if refund_pol else ""

        with st.form("refunds_policy_form"):
            refund_text = st.text_area(
                "Refund Processing & Eligibility",
                value=current_refund_content,
                placeholder="e.g. Refunds are processed to the original payment method within 5-7 business days of receiving the item.",
                height=150,
            )
            save_refund = st.form_submit_button("Save Refund Policy", type="primary")

            if save_refund:
                if not refund_text.strip():
                    st.error("Policy content cannot be empty.")
                else:
                    try:
                        policy_service.create_or_update_policy(
                            business_id=biz.business_id,
                            policy_type="refunds",
                            content=refund_text.strip(),
                        )
                        st.success("✅ Refund policy saved successfully!")
                        st.rerun()
                    except ValidationError as e:
                        handle_validation_error(e)

    # 4. CUSTOM POLICY TAB
    with tabs[3]:
        st.subheader("➕ Add or Update Custom Policy")
        with st.form("custom_policy_form"):
            custom_type = st.text_input("Policy Type *", placeholder="e.g. payment, sizing, privacy, warranty")
            custom_content = st.text_area("Policy Content *", placeholder="Enter policy details...", height=150)
            save_custom = st.form_submit_button("Save Custom Policy", type="primary")

            if save_custom:
                if not custom_type.strip() or not custom_content.strip():
                    st.error("Both Policy Type and Content are required.")
                else:
                    try:
                        policy_service.create_or_update_policy(
                            business_id=biz.business_id,
                            policy_type=custom_type.strip(),
                            content=custom_content.strip(),
                        )
                        st.success(f"✅ Policy '{custom_type.strip()}' saved successfully!")
                        st.rerun()
                    except ValidationError as e:
                        handle_validation_error(e)

    # 5. ALL POLICIES OVERVIEW & DELETION TAB
    with tabs[4]:
        st.subheader(f"All Policies for {biz.name} ({len(policies)})")
        if not policies:
            st.info("No policies defined yet.")
        else:
            for pol in policies:
                with st.expander(f"📜 **{pol.policy_type.capitalize()} Policy**"):
                    st.write(pol.content)
                    st.caption(f"Last updated: `{pol.updated_at}`")

                    if st.checkbox("Confirm Delete", key=f"del_pol_chk_{pol.policy_id}"):
                        if st.button("🗑️ Delete Policy", key=f"del_pol_btn_{pol.policy_id}", type="primary"):
                            if policy_service.delete_policy(pol.policy_id, business_id=biz.business_id):
                                st.success(f"Policy '{pol.policy_type}' deleted.")
                                st.rerun()
