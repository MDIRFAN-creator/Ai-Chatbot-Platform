"""FAQ management page for SupportBot AI."""

from pydantic import ValidationError
import streamlit as st

from app.components.common import render_header, require_business_context
from app.components.forms import handle_validation_error
from core.models import FAQCreate, FAQUpdate
from services.faq_service import faq_service


def render_faqs_page() -> None:
    """Render the FAQ management interface."""
    render_header(
        "❓ Frequently Asked Questions (FAQs)",
        "Define common customer questions and official business answers for your AI assistant.",
    )

    biz = require_business_context()
    if not biz:
        return

    faqs = faq_service.get_faqs_by_business(biz.business_id)

    tabs = st.tabs(["📋 View FAQs", "➕ Add New FAQ", "✏️ Edit FAQ"])

    # 1. VIEW FAQS TAB
    with tabs[0]:
        st.subheader(f"FAQ Items for {biz.name} ({len(faqs)})")
        if not faqs:
            st.info("No FAQs added yet. Use the **Add New FAQ** tab to add your first question and answer.")
        else:
            for faq in faqs:
                with st.expander(f"**Q: {faq.question}**"):
                    st.markdown(f"**Answer:**\n\n{faq.answer}")
                    st.caption(f"ID: `{faq.faq_id}` | Updated: `{faq.updated_at}`")

                    if st.checkbox("Confirm Delete", key=f"faq_del_chk_{faq.faq_id}"):
                        if st.button("🗑️ Delete FAQ", key=f"faq_del_btn_{faq.faq_id}", type="primary"):
                            if faq_service.delete_faq(faq.faq_id, business_id=biz.business_id):
                                st.success("FAQ deleted.")
                                st.rerun()

    # 2. ADD FAQ TAB
    with tabs[1]:
        st.subheader("Add a New FAQ")
        with st.form("add_faq_form", clear_on_submit=True):
            q_text = st.text_input("Customer Question *", placeholder="e.g. Do you ship to Canada?")
            a_text = st.text_area("Official Answer *", placeholder="e.g. Yes, we ship to Canada via standard international delivery.", height=120)
            submit_faq = st.form_submit_button("Save FAQ", type="primary")

            if submit_faq:
                try:
                    create_data = FAQCreate(
                        business_id=biz.business_id,
                        question=q_text,
                        answer=a_text,
                    )
                    new_faq = faq_service.create_faq(create_data)
                    st.success(f"✅ FAQ saved successfully!")
                    st.rerun()
                except ValidationError as e:
                    handle_validation_error(e)
                except Exception as e:
                    st.error(f"Error adding FAQ: {str(e)}")

    # 3. EDIT FAQ TAB
    with tabs[2]:
        st.subheader("Edit Existing FAQ")
        if not faqs:
            st.info("No FAQs available to edit.")
        else:
            faq_options = {f.faq_id: f.question for f in faqs}
            selected_fid = st.selectbox(
                "Select FAQ to Edit:",
                options=list(faq_options.keys()),
                format_func=lambda fid: faq_options.get(fid, fid),
            )

            selected_faq = faq_service.get_faq(selected_fid, business_id=biz.business_id)
            if selected_faq:
                with st.form(f"edit_faq_form_{selected_faq.faq_id}"):
                    eq_text = st.text_input("Question *", value=selected_faq.question)
                    ea_text = st.text_area("Answer *", value=selected_faq.answer, height=120)
                    submit_edit = st.form_submit_button("Update FAQ", type="primary")

                    if submit_edit:
                        try:
                            update_data = FAQUpdate(question=eq_text, answer=ea_text)
                            updated_faq = faq_service.update_faq(
                                selected_faq.faq_id,
                                update_data,
                                business_id=biz.business_id,
                            )
                            if updated_faq:
                                st.success("✅ FAQ updated successfully!")
                                st.rerun()
                        except ValidationError as e:
                            handle_validation_error(e)
                        except Exception as e:
                            st.error(f"Error updating FAQ: {str(e)}")
