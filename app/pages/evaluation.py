"""Streamlit Evaluation Dashboard for SupportBot AI.

Provides an interactive benchmark UI allowing developers and business owners to:
1. Inspect the evaluation dataset.
2. Filter test suites by category and turn type.
3. Execute automated benchmarks against the RAG chatbot.
4. Visualize high-level metrics and category score breakdowns.
5. Inspect individual test cases and failure diagnostics.
6. Export Markdown and JSON benchmark reports.
"""

from typing import List, Optional
import pandas as pd
import streamlit as st

from evaluation.metrics import CaseEvaluationResult, EvaluationSummaryMetrics
from evaluation.report import generate_json_report, generate_markdown_report
from evaluation.runner import EvaluationRunner
from evaluation.test_cases import load_evaluation_dataset


def render_evaluation_page() -> None:
    """Render the full interactive Evaluation Dashboard."""
    st.title("🧪 RAG Evaluation Benchmark Dashboard")
    st.markdown(
        "Automated benchmarking subsystem for evaluating RAG retrieval relevance, "
        "answer correctness, groundedness, safe abstention, and tenant isolation."
    )

    try:
        full_dataset = load_evaluation_dataset()
    except Exception as exc:
        st.error(f"❌ Failed to load evaluation dataset: {exc}")
        return

    # Dataset metadata header
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Dataset", "UrbanThreads V1")
    with col2:
        st.metric("Total Cases", full_dataset.total_cases)
    with col3:
        st.metric("Target Tenant", full_dataset.business_id)
    with col4:
        st.metric("Dataset Version", full_dataset.version)

    st.markdown("---")

    # Suite Configuration & Filtering
    st.subheader("⚙️ Benchmark Configuration")
    categories = ["All Categories"] + sorted(list(set(c.category for c in full_dataset.cases)))

    cfg_col1, cfg_col2, cfg_col3 = st.columns([2, 1, 1])
    with cfg_col1:
        selected_category = st.selectbox("Filter by Category", categories, index=0)
    with cfg_col2:
        turn_filter = st.selectbox("Turn Type", ["All Types", "Single-turn only", "Multi-turn only"], index=0)
    with cfg_col3:
        st.write("")
        st.write("")
        run_btn = st.button("🚀 Run Benchmark", type="primary", use_container_width=True)

    cat_filter = None if selected_category == "All Categories" else selected_category
    type_filter = None
    if turn_filter == "Single-turn only":
        type_filter = "single_turn"
    elif turn_filter == "Multi-turn only":
        type_filter = "multi_turn"

    # Execution State
    if run_btn:
        runner = EvaluationRunner()
        filtered_ds = load_evaluation_dataset(category=cat_filter, case_type=type_filter)

        progress_bar = st.progress(0, text="Initializing evaluation environment...")
        status_text = st.empty()

        def on_progress(idx: int, total: int, case_id: str):
            pct = int((idx / total) * 100)
            progress_bar.progress(pct, text=f"Evaluating Case {case_id} ({idx}/{total})...")

        with st.spinner("Running automated RAG benchmark..."):
            metrics, results = runner.run_suite(
                dataset=filtered_ds,
                progress_callback=on_progress,
            )

        progress_bar.empty()
        status_text.success(
            f"✅ Benchmark Complete! Evaluated {metrics.total_cases} cases in {metrics.average_latency_seconds * metrics.total_cases:.2f}s."
        )

        st.session_state["last_eval_metrics"] = metrics
        st.session_state["last_eval_results"] = results

    # Display Results if available in session state
    if "last_eval_metrics" in st.session_state and "last_eval_results" in st.session_state:
        metrics: EvaluationSummaryMetrics = st.session_state["last_eval_metrics"]
        results: List[CaseEvaluationResult] = st.session_state["last_eval_results"]

        st.markdown("---")
        st.subheader("📊 Benchmark Results")

        # 5 Core Pillar Metrics
        m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
        with m_col1:
            st.metric("Overall Score", f"{metrics.overall_score_pct}%")
        with m_col2:
            st.metric("Retrieval", f"{metrics.retrieval_relevance_pct}%")
        with m_col3:
            st.metric("Correctness", f"{metrics.answer_correctness_pct}%")
        with m_col4:
            st.metric("Groundedness", f"{metrics.groundedness_pct}%")
        with m_col5:
            st.metric("Abstention", f"{metrics.abstention_quality_pct}%")
        with m_col6:
            st.metric("Isolation", f"{metrics.tenant_isolation_pct}%")

        # Secondary Metrics
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            st.metric("Prompt Injection Defense", f"{metrics.prompt_injection_pct}%")
        with s_col2:
            st.metric("Passed / Total", f"{metrics.passed_cases} / {metrics.total_cases}")
        with s_col3:
            st.metric("Avg Response Time", f"{metrics.average_latency_seconds}s")

        st.markdown("---")

        # Category Breakdown Table
        st.subheader("📈 Category Breakdown")
        table_rows = []
        for cat, c_data in sorted(metrics.category_metrics.items()):
            table_rows.append({
                "Category": cat,
                "Total Cases": c_data.total_cases,
                "Passed": c_data.passed_cases,
                "Pass Rate": f"{c_data.pass_rate_pct}%",
                "Avg Correctness": f"{c_data.avg_correctness_score}%",
                "Avg Latency": f"{c_data.avg_latency_seconds}s",
            })
        if table_rows:
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

        st.markdown("---")

        # Diagnostic Case Inspector
        st.subheader("🔍 Case Inspector & Failure Diagnostics")
        filter_status = st.radio(
            "Filter Cases Displayed",
            ["All Cases", "Failed Cases Only", "Passed Cases Only"],
            horizontal=True,
        )

        displayed_results = results
        if filter_status == "Failed Cases Only":
            displayed_results = [r for r in results if not r.passed]
        elif filter_status == "Passed Cases Only":
            displayed_results = [r for r in results if r.passed]

        st.caption(f"Showing {len(displayed_results)} test cases.")

        for r in displayed_results:
            icon = "✅" if r.passed else "❌"
            header = f"{icon} [{r.case_id}] {r.category} — {r.question[:70]}"
            with st.expander(header, expanded=not r.passed):
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    st.markdown(f"**Question**: {r.question}")
                    st.markdown(f"**Expected Answer**: `{r.expected_answer}`")
                with d_col2:
                    st.markdown(f"**Actual Answer**: {r.actual_answer}")
                    st.markdown(f"**Fallback Triggered**: `{r.fallback_triggered}` | **Latency**: `{r.latency_seconds}s`")

                if not r.passed:
                    st.error(f"**Primary Failure Reason**: {r.primary_failure_reason}")

                # Evaluator Scores Breakdown
                st.markdown("**Evaluator Scores:**")
                e1, e2, e3, e4, e5, e6 = st.columns(6)
                e1.caption(f"Retrieval: {r.retrieval_result.score:.1f}")
                e2.caption(f"Correctness: {r.correctness_result.score:.1f}")
                e3.caption(f"Grounded: {r.groundedness_result.score:.1f}")
                e4.caption(f"Abstention: {r.abstention_result.score:.1f}")
                e5.caption(f"Injection: {r.injection_result.score:.1f}")
                e6.caption(f"Isolation: {r.isolation_result.score:.1f}")

                # Retrieved Context Preview
                if r.retrieved_documents:
                    with st.expander(f"Retrieved Context ({len(r.retrieved_documents)} documents)"):
                        for idx, d in enumerate(r.retrieved_documents, start=1):
                            st.caption(
                                f"Doc #{idx} | {d.metadata.get('source_type', 'unknown').upper()} ({d.metadata.get('source_id', '')})"
                            )
                            st.text(d.page_content)

        st.markdown("---")

        # Export Reports
        st.subheader("📥 Export Reports")
        rep_col1, rep_col2 = st.columns(2)
        with rep_col1:
            md_content = generate_markdown_report(metrics, results)
            st.download_button(
                "📥 Download Markdown Report",
                data=md_content,
                file_name="evaluation_report.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with rep_col2:
            json_content = generate_json_report(metrics, results)
            st.download_button(
                "📥 Download JSON Report",
                data=json_content,
                file_name="evaluation_report.json",
                mime="application/json",
                use_container_width=True,
            )
