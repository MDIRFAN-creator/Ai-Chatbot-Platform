"""Streamlit Chatbot Preview & Interactive Testing Page for SupportBot AI.

Enables business owners and developers to test the live RAG assistant
within the Streamlit dashboard before deploying the widget.
"""

from typing import Dict, List, Optional
import uuid
import streamlit as st

from app.components.common import render_header, require_business_context
from core.database import DatabaseManager
from services.chatbot_service import chatbot_service


def render_chatbot_page() -> None:
    """Render the interactive Chatbot Preview testing interface."""
    render_header(
        "💬 Chatbot Preview & Testing",
        "Interact with your business-grounded RAG assistant in real time to verify responses and grounding.",
    )

    business = require_business_context()
    if not business:
        return

    business_id = business.business_id
    db = DatabaseManager()
    settings = db.get_assistant_settings(business_id)

    assistant_name = settings.assistant_name if settings else f"{business.name} Assistant"
    welcome_msg = (
        settings.welcome_message
        if settings
        else f"Hi! Welcome to {business.name}. How can I help you today?"
    )

    # Initialize chat session state for this business
    chat_key = f"chat_messages_{business_id}"
    session_key = f"chat_session_{business_id}"

    if session_key not in st.session_state:
        st.session_state[session_key] = f"preview_sess_{uuid.uuid4().hex[:8]}"

    if chat_key not in st.session_state:
        st.session_state[chat_key] = [
            {"role": "assistant", "content": welcome_msg, "retrieved_docs": [], "fallback": False}
        ]

    # Header Controls
    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.caption(f"Assistant: **{assistant_name}** • Tenant: `{business_id}` • Session: `{st.session_state[session_key]}`")
    with top_col2:
        if st.button("🧹 Reset Chat", use_container_width=True):
            st.session_state[session_key] = f"preview_sess_{uuid.uuid4().hex[:8]}"
            st.session_state[chat_key] = [
                {"role": "assistant", "content": welcome_msg, "retrieved_docs": [], "fallback": False}
            ]
            st.rerun()

    st.divider()

    # Render Chat History
    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("retrieved_docs"):
                with st.expander(f"📚 Retrieved Context ({len(msg['retrieved_docs'])} docs)"):
                    for idx, doc in enumerate(msg["retrieved_docs"], start=1):
                        st.caption(
                            f"Doc #{idx} • Source: `{doc.metadata.get('source_type', 'unknown')}` ({doc.metadata.get('source_id', '')})"
                        )
                        st.text(doc.page_content)
            if msg.get("fallback"):
                st.caption("⚠️ *Safe fallback triggered (grounding threshold applied)*")

    # Chat Input
    if user_prompt := st.chat_input(f"Message {assistant_name}..."):
        # Append User Message
        st.session_state[chat_key].append(
            {"role": "user", "content": user_prompt, "retrieved_docs": [], "fallback": False}
        )
        with st.chat_message("user"):
            st.write(user_prompt)

        # Generate Assistant Response
        with st.chat_message("assistant"):
            with st.spinner("Searching knowledge base..."):
                try:
                    response = chatbot_service.answer(
                        business_id=business_id,
                        session_id=st.session_state[session_key],
                        question=user_prompt,
                    )
                    answer_text = response.answer
                    retrieved = response.retrieved_documents
                    fallback = response.fallback_triggered
                except Exception as exc:
                    answer_text = f"❌ An error occurred: {exc}"
                    retrieved = []
                    fallback = True

            st.write(answer_text)
            if retrieved:
                with st.expander(f"📚 Retrieved Context ({len(retrieved)} docs)"):
                    for idx, doc in enumerate(retrieved, start=1):
                        st.caption(
                            f"Doc #{idx} • Source: `{doc.metadata.get('source_type', 'unknown')}` ({doc.metadata.get('source_id', '')})"
                        )
                        st.text(doc.page_content)
            if fallback:
                st.caption("⚠️ *Safe fallback triggered (grounding threshold applied)*")

        # Save Assistant Message to session state
        st.session_state[chat_key].append(
            {
                "role": "assistant",
                "content": answer_text,
                "retrieved_docs": retrieved,
                "fallback": fallback,
            }
        )
