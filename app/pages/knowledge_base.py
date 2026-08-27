"""Knowledge Base Management Page for SupportBot AI Streamlit Dashboard."""

from typing import Optional
import streamlit as st

from app.components.common import render_header
from core.models import Business
from services.business_service import business_service
from services.knowledge_service import knowledge_service


def render_knowledge_base_page() -> None:
    """Render the Knowledge Base builder and management page."""
    render_header(
        "📚 Knowledge Base Builder",
        "Normalize structured business data into LangChain documents and generate business-scoped FAISS vector indices.",
    )

    business_id: Optional[str] = st.session_state.get("business_id")
    if not business_id:
        st.warning("⚠️ No active business selected. Please select or create a business in **Business Setup** first.")
        return

    current_biz: Optional[Business] = business_service.get_business(business_id)
    if not current_biz:
        st.error("❌ Selected business could not be found.")
        return

    # Retrieve current knowledge status
    status = knowledge_service.get_knowledge_base_status(business_id)
    source_counts = status.get("source_counts", {})
    norm_count = status.get("normalized_documents_count", 0)
    index_ready = status.get("faiss_index_ready", False)
    vector_path = status.get("vector_store_path", "N/A")

    # Overview Metrics Cards
    st.subheader(f"Tenant: **{current_biz.name}** (`{business_id}`)")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Structured Sources",
            value=sum(source_counts.values()),
            help=f"Business: {source_counts.get('business', 0)}, Products: {source_counts.get('products', 0)}, Policies: {source_counts.get('policies', 0)}, FAQs: {source_counts.get('faqs', 0)}",
        )
    with col2:
        st.metric(
            label="Normalized Documents",
            value=norm_count,
            help="Knowledge documents persisted in SQLite table 'knowledge_documents'",
        )
    with col3:
        st.metric(
            label="FAISS Index Status",
            value="🟢 Ready" if index_ready else "⚪ Not Built",
        )
    with col4:
        st.metric(
            label="Embedding Model",
            value="all-MiniLM-L6-v2",
            help="sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)",
        )

    st.markdown("---")

    # Build / Rebuild Action Section
    st.markdown("### 🔄 Knowledge Base Index Generation")
    st.caption(
        "Generates normalized LangChain documents from current SQLite records and builds an isolated, "
        "tenant-scoped FAISS vector index on disk."
    )

    if st.button("🚀 Build / Regenerate Knowledge Base", type="primary", use_container_width=True):
        with st.spinner("Building normalized documents and generating embeddings..."):
            try:
                result = knowledge_service.build_knowledge_base(business_id)
                st.success(
                    f"✅ **Knowledge Base generated successfully!**\n\n"
                    f"- **Normalized Documents Persisted:** {result.get('normalized_documents_count', 0)}\n"
                    f"- **Stale Records Purged:** {result.get('stale_documents_purged', 0)}\n"
                    f"- **Vector Index Path:** `{result.get('vector_store_path')}`\n"
                    f"- **FAISS Index Status:** {'Ready' if result.get('faiss_index_ready') else 'Empty'}"
                )
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to build knowledge base: {str(e)}")

    st.markdown("---")

    # Normalized Documents Preview
    st.markdown("### 📑 Persisted Knowledge Documents")
    kdocs = knowledge_service.get_knowledge_documents(business_id)

    if not kdocs:
        st.info("ℹ️ No normalized knowledge documents found. Click **Build / Regenerate Knowledge Base** above to generate them.")
    else:
        st.caption(f"Showing **{len(kdocs)}** normalized document(s) in SQLite for tenant `{business_id}`:")
        for idx, doc in enumerate(kdocs, start=1):
            source_type_icon = {
                "business": "🏢",
                "product": "🛍️",
                "policy": "📜",
                "faq": "❓",
            }.get(doc.source_type, "📄")

            with st.expander(
                f"{source_type_icon} **Doc #{idx}** — [{doc.source_type.upper()}] {doc.source_id}",
                expanded=False,
            ):
                st.code(doc.content, language="markdown")
                st.json(doc.metadata)

    st.markdown("---")
    st.caption(f"📁 Vector Store Directory: `{vector_path}`")
