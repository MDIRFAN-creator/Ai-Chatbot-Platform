"""Business onboarding and profile setup page."""

from pydantic import ValidationError
import streamlit as st

from app.components.common import get_current_business, render_header
from app.components.forms import handle_validation_error
from core.models import BusinessCreate, BusinessUpdate
from services.business_service import business_service


def render_business_setup_page() -> None:
    """Render the business onboarding and configuration interface."""
    render_header(
        "🏢 Business Profile & Setup",
        "Configure your business details, contact information, and operating presence.",
    )

    current_biz = get_current_business()
    tab_labels = ["➕ Create New Business"]
    if current_biz:
        tab_labels.append("✏️ Edit Current Business")

    tabs = st.tabs(tab_labels)

    # 1. CREATE NEW BUSINESS TAB
    with tabs[0]:
        st.subheader("Register a New Business")
        with st.form("create_business_form", clear_on_submit=True):
            name = st.text_input("Business Name *", placeholder="e.g. UrbanThreads Apparel")
            industry = st.text_input("Industry / Niche", placeholder="e.g. Fashion & Apparel")
            description = st.text_area("Business Description", placeholder="e.g. Modern streetwear brand providing premium urban clothing.")
            website = st.text_input("Website URL", placeholder="https://urbanthreads.example.com")

            col1, col2 = st.columns(2)
            with col1:
                email = st.text_input("Customer Support Email", placeholder="support@urbanthreads.example.com")
            with col2:
                phone = st.text_input("Customer Support Phone", placeholder="+1-800-555-0199")

            location = st.text_input("Location / Headquarters", placeholder="e.g. New York, NY")

            submitted = st.form_submit_button("Create Business", type="primary")

            if submitted:
                try:
                    create_data = BusinessCreate(
                        name=name,
                        industry=industry or None,
                        description=description or None,
                        website=website or None,
                        contact_email=email or None,
                        contact_phone=phone or None,
                        location=location or None,
                    )
                    new_biz = business_service.create_business(create_data)
                    st.session_state["business_id"] = new_biz.business_id
                    st.success(f"✅ Business **{new_biz.name}** created successfully! Set as active business.")
                    st.rerun()
                except ValidationError as e:
                    handle_validation_error(e)
                except Exception as e:
                    st.error(f"Error creating business: {str(e)}")

    # 2. EDIT CURRENT BUSINESS TAB
    if current_biz and len(tabs) > 1:
        with tabs[1]:
            st.subheader(f"Edit Profile for: {current_biz.name}")
            with st.form("edit_business_form"):
                edit_name = st.text_input("Business Name *", value=current_biz.name)
                edit_industry = st.text_input("Industry / Niche", value=current_biz.industry or "")
                edit_desc = st.text_area("Business Description", value=current_biz.description or "")
                edit_website = st.text_input("Website URL", value=current_biz.website or "")

                col1, col2 = st.columns(2)
                with col1:
                    edit_email = st.text_input("Customer Support Email", value=current_biz.contact_email or "")
                with col2:
                    edit_phone = st.text_input("Customer Support Phone", value=current_biz.contact_phone or "")

                edit_location = st.text_input("Location / Headquarters", value=current_biz.location or "")

                update_submitted = st.form_submit_button("Save Changes", type="primary")

                if update_submitted:
                    try:
                        update_data = BusinessUpdate(
                            name=edit_name,
                            industry=edit_industry or None,
                            description=edit_desc or None,
                            website=edit_website or None,
                            contact_email=edit_email or None,
                            contact_phone=edit_phone or None,
                            location=edit_location or None,
                        )
                        updated_biz = business_service.update_business(current_biz.business_id, update_data)
                        if updated_biz:
                            st.success(f"✅ Business **{updated_biz.name}** updated successfully!")
                            st.rerun()
                        else:
                            st.error("Business could not be updated.")
                    except ValidationError as e:
                        handle_validation_error(e)
                    except Exception as e:
                        st.error(f"Error updating business: {str(e)}")
