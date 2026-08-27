"""Streamlit Embed Code Generator Page for SupportBot AI.

Allows business owners to customize, test, and generate the embeddable JavaScript
widget snippet for their website, with live visual preview and configuration persistence.
"""

from typing import Optional
import streamlit as st
import streamlit.components.v1 as components

from app.components.common import render_header, require_business_context
from core.config import get_config
from core.database import DatabaseManager
from core.models import AssistantSettingsUpdate


def render_embed_page() -> None:
    """Render the interactive Merchant Embed Widget & Integration page."""
    render_header(
        "🔌 Embed Chatbot Widget",
        "Configure your AI assistant's identity and generate a one-line JavaScript snippet for your storefront.",
    )

    business = require_business_context()
    if not business:
        return

    business_id = business.business_id
    db = DatabaseManager()
    cfg = get_config()
    settings = db.get_assistant_settings(business_id)

    default_name = settings.assistant_name if settings and settings.assistant_name else f"{business.name} Assistant"
    default_tone = settings.tone if settings and settings.tone else "friendly and professional"
    default_welcome = (
        settings.welcome_message
        if settings and settings.welcome_message
        else f"Hi there! 👋 Welcome to {business.name}. How can I assist you today?"
    )

    # -----------------------------------------------------------------
    # SECTION A: YOUR CHATBOT OVERVIEW
    # -----------------------------------------------------------------
    st.markdown("### 🤖 Your Chatbot")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Store Tenant", business.name)
    with m2:
        st.metric("Business ID", business_id)
    with m3:
        st.metric("Assistant Name", default_name)
    with m4:
        st.metric("Integration Status", "🟢 Ready to Embed")

    st.divider()

    # -----------------------------------------------------------------
    # SECTION B: CONFIGURE WIDGET
    # -----------------------------------------------------------------
    st.markdown("### 🎨 Configure Widget")
    st.caption("Customize how your AI chatbot appears and greets customers on your website.")

    col1, col2 = st.columns(2)

    with col1:
        custom_title = st.text_input(
            "Chatbot Title / Display Name",
            value=default_name,
            help="The title displayed at the top of the chat window.",
        )
        assistant_tone = st.text_input(
            "Tone of Voice",
            value=default_tone,
            help="Instruction given to the AI for its conversational persona.",
        )
        primary_color = st.color_picker(
            "Brand / Accent Color",
            value="#111827",
            help="Color applied to the launcher button, header banner, and customer chat bubbles.",
        )

    with col2:
        position = st.selectbox(
            "Launcher Position",
            ["bottom-right", "bottom-left"],
            index=0,
            help="Corner of the browser window where the floating chat button appears.",
        )
        widget_enabled = st.toggle(
            "Enable Widget on Storefront",
            value=True,
            help="When disabled, the widget script will automatically suppress rendering on the store.",
        )
        target_env = st.radio(
            "Deployment Target:",
            ["Local Development", "Production Server"],
            index=0,
            horizontal=True,
        )

    welcome_msg = st.text_area(
        "Welcome Greeting",
        value=default_welcome,
        height=75,
        help="Initial greeting displayed when a shopper opens the chat window.",
    )

    # Save Settings Button
    if st.button("💾 Save Widget Configuration", type="primary"):
        db.create_or_update_assistant_settings(
            AssistantSettingsUpdate(
                assistant_name=custom_title.strip() if custom_title else default_name,
                tone=assistant_tone.strip() if assistant_tone else default_tone,
                welcome_message=welcome_msg.strip() if welcome_msg else default_welcome,
            ),
            business_id=business_id,
        )
        st.success("✅ Widget configuration saved to database successfully!")
        st.rerun()

    st.divider()

    # -----------------------------------------------------------------
    # SECTION C: INSTALL ON YOUR WEBSITE
    # -----------------------------------------------------------------
    st.markdown("### 📋 Install on Your Website")
    st.markdown(
        "Copy and paste this single `<script>` tag into the `<head>` or before the closing `</body>` tag of your website HTML:"
    )

    if target_env == "Local Development":
        script_src = f"http://localhost:{cfg.api_port}/widget/embed.js"
        api_url = f"http://localhost:{cfg.api_port}/api/chat"
    else:
        script_src = "https://api.yourdomain.com/widget/embed.js"
        api_url = "https://api.yourdomain.com/api/chat"

    disabled_attr = '\n    data-disabled="true"' if not widget_enabled else ""

    snippet_code = f"""<!-- SupportBot AI Embed for {business.name} -->
<script
    src="{script_src}"
    data-business-id="{business_id}"
    data-api-url="{api_url}"
    data-title="{custom_title}"
    data-welcome-message="{welcome_msg}"
    data-primary-color="{primary_color}"
    data-position="{position}"{disabled_attr}>
</script>"""

    st.code(snippet_code, language="html")

    with st.expander("📖 Platform-Specific Installation Guides", expanded=False):
        t1, t2, t3, t4 = st.tabs(["Custom HTML", "Shopify", "WooCommerce", "WordPress"])
        with t1:
            st.markdown("""
            1. Open your `index.html` or main template file.
            2. Paste the snippet directly before the closing `</body>` tag.
            3. Save and refresh your website.
            """)
        with t2:
            st.markdown("""
            1. In Shopify Admin, go to **Online Store** -> **Themes**.
            2. Click **...** (Actions) -> **Edit code**.
            3. Open `layout/theme.liquid`.
            4. Paste the snippet right before the `</body>` tag and click **Save**.
            """)
        with t3:
            st.markdown("""
            1. In WordPress Admin, go to **Appearance** -> **Theme File Editor**.
            2. Open `footer.php`.
            3. Paste the snippet immediately before `<?php wp_footer(); ?>` or `</body>`.
            """)
        with t4:
            st.markdown("""
            1. Install a header/footer scripts plugin (e.g. *WPCode* or *Insert Headers and Footers*).
            2. Paste the snippet into the **Footer Scripts** section.
            3. Click **Save Changes**.
            """)

    st.divider()

    # -----------------------------------------------------------------
    # SECTION D: LIVE PREVIEW & TEST STOREFRONT
    # -----------------------------------------------------------------
    st.markdown("### 👁️ Live Preview & Test Storefront")
    st.caption("Test the interactive launcher button and responsive modal.")

    # Read widget JS for the iframe preview
    try:
        with open("widget/embed.js", "r", encoding="utf-8") as f:
            widget_js = f.read()
    except Exception:
        widget_js = ""

    preview_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        body {{
          margin: 0;
          padding: 24px;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          background: #f9fafb;
          min-height: 460px;
        }}
        .store-header {{
          background: #ffffff;
          border-radius: 12px;
          padding: 20px;
          border: 1px solid #e5e7eb;
          box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .store-title {{
          font-size: 18px;
          font-weight: 700;
          color: #111827;
        }}
        .store-sub {{
          color: #6b7280;
          font-size: 13.5px;
          margin-top: 4px;
        }}
      </style>
    </head>
    <body>
      <div class="store-header">
        <div class="store-title">{business.name} Storefront Preview</div>
        <div class="store-sub">The floating support assistant is positioned in the <strong>{position}</strong> corner.</div>
      </div>

      <script>
        window.SupportBotConfig = {{
          businessId: "{business_id}",
          apiUrl: "{api_url}",
          title: "{custom_title}",
          welcomeMessage: "{welcome_msg}",
          primaryColor: "{primary_color}",
          position: "{position}",
          disabled: {str(not widget_enabled).lower()}
        }};
      </script>
      <script>
        {widget_js}
      </script>
    </body>
    </html>
    """

    components.html(preview_html, height=540, scrolling=True)

    st.info(
        f"🌐 **External Storefront Demo**: You can also test the standalone reference storefront by opening "
        f"`widget/test_page.html` in your browser while Uvicorn is running on port {cfg.api_port}."
    )
