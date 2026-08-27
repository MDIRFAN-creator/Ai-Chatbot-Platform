"""AI Assistant settings configuration page."""

from pydantic import ValidationError
import streamlit as st

from app.components.common import render_header, require_business_context
from app.components.forms import handle_validation_error
from core.models import AssistantSettingsCreate, AssistantSettingsUpdate
from services.assistant_service import assistant_service


def render_assistant_settings_page() -> None:
    """Render the AI assistant personality and settings configuration interface."""
    render_header(
        "🤖 AI Assistant Settings",
        "Customize your AI customer support assistant's persona, tone of voice, and greeting.",
    )

    biz = require_business_context()
    if not biz:
        return

    current_settings = assistant_service.get_assistant_settings(biz.business_id)

    default_name = current_settings.assistant_name if current_settings else f"{biz.name} Assistant"
    default_tone = current_settings.tone if current_settings else "Friendly, professional, and concise"
    default_welcome = (
        current_settings.welcome_message
        if current_settings
        else f"Hi! Welcome to {biz.name}. How can I assist you today?"
    )

    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.subheader("Configuration")
        with st.form("assistant_settings_form"):
            asst_name = st.text_input(
                "Assistant Name *",
                value=default_name,
                placeholder="e.g. UrbanThreads Assistant",
            )
            asst_tone = st.text_input(
                "Personality & Tone of Voice",
                value=default_tone,
                placeholder="e.g. Friendly, empathetic, and professional",
            )
            asst_welcome = st.text_area(
                "Welcome / Greeting Message",
                value=default_welcome,
                placeholder="Initial message displayed when customer opens the chat widget...",
                height=120,
            )

            submit_asst = st.form_submit_button("Save Assistant Settings", type="primary")

            if submit_asst:
                try:
                    create_data = AssistantSettingsCreate(
                        business_id=biz.business_id,
                        assistant_name=asst_name,
                        tone=asst_tone or None,
                        welcome_message=asst_welcome or None,
                    )
                    saved = assistant_service.create_or_update_assistant_settings(
                        create_data, business_id=biz.business_id
                    )
                    st.success(f"✅ Assistant settings for **{saved.assistant_name}** saved successfully!")
                    st.rerun()
                except ValidationError as e:
                    handle_validation_error(e)
                except Exception as e:
                    st.error(f"Error saving assistant settings: {str(e)}")

    with right_col:
        st.subheader("👁️ Live Greeting Preview")
        st.caption("This is how the initial welcome greeting will appear in the customer chat widget:")

        # Chat Bubble Preview
        st.markdown(
            f"""
            <div style="background-color: #f0f2f6; border-radius: 12px; padding: 16px; border-left: 4px solid #4F46E5; margin-top: 10px; color: #1e293b;">
                <div style="font-weight: 600; font-size: 0.9em; margin-bottom: 6px;">🤖 {default_name}</div>
                <div style="font-size: 0.95em;">{default_welcome}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown(f"**Persona Tone:** *{default_tone}*")
        st.caption("Note: Chatbot responses and RAG generation will be activated in later phases.")
