"""Evaluation Reporting Engine for SupportBot AI.

Generates structured evaluation reports in:
1. Python Dictionary / Structured object format
2. JSON serialization format
3. GitHub-flavored Markdown tables with diagnostic failure breakdowns.
"""

import json
from typing import Any, Dict, List

from evaluation.metrics import CaseEvaluationResult, EvaluationSummaryMetrics


def generate_dict_report(
    metrics: EvaluationSummaryMetrics,
    results: List[CaseEvaluationResult],
) -> Dict[str, Any]:
    """Generate a comprehensive dictionary report from an evaluation run."""
    cases_data = []
    for r in results:
        cases_data.append({
            "case_id": r.case_id,
            "category": r.category,
            "question": r.question,
            "expected_answer": r.expected_answer,
            "actual_answer": r.actual_answer,
            "passed": r.passed,
            "fallback_triggered": r.fallback_triggered,
            "latency_seconds": r.latency_seconds,
            "retrieved_doc_count": len(r.retrieved_documents),
            "primary_failure_reason": r.primary_failure_reason,
            "evaluator_scores": {
                "retrieval_relevance": r.retrieval_result.score,
                "answer_correctness": r.correctness_result.score,
                "groundedness": r.groundedness_result.score,
                "abstention_quality": r.abstention_result.score,
                "tenant_isolation": r.isolation_result.score,
                "prompt_injection": r.injection_result.score,
            },
        })

    category_data = {}
    for cat, c_metric in metrics.category_metrics.items():
        category_data[cat] = {
            "total_cases": c_metric.total_cases,
            "passed_cases": c_metric.passed_cases,
            "pass_rate_pct": c_metric.pass_rate_pct,
            "avg_correctness_score": c_metric.avg_correctness_score,
            "avg_latency_seconds": c_metric.avg_latency_seconds,
        }

    return {
        "summary": {
            "total_cases": metrics.total_cases,
            "passed_cases": metrics.passed_cases,
            "failed_cases": metrics.failed_cases,
            "overall_score_pct": metrics.overall_score_pct,
            "retrieval_relevance_pct": metrics.retrieval_relevance_pct,
            "answer_correctness_pct": metrics.answer_correctness_pct,
            "groundedness_pct": metrics.groundedness_pct,
            "abstention_quality_pct": metrics.abstention_quality_pct,
            "tenant_isolation_pct": metrics.tenant_isolation_pct,
            "prompt_injection_pct": metrics.prompt_injection_pct,
            "average_latency_seconds": metrics.average_latency_seconds,
        },
        "categories": category_data,
        "cases": cases_data,
    }


def generate_json_report(
    metrics: EvaluationSummaryMetrics,
    results: List[CaseEvaluationResult],
    indent: int = 2,
) -> str:
    """Serialize the evaluation results into formatted JSON."""
    dict_report = generate_dict_report(metrics, results)
    return json.dumps(dict_report, indent=indent, ensure_ascii=False)


def generate_markdown_report(
    metrics: EvaluationSummaryMetrics,
    results: List[CaseEvaluationResult],
) -> str:
    """Generate a GitHub-flavored Markdown evaluation report."""
    md_lines = [
        "# SupportBot AI — RAG Evaluation Benchmark Report",
        "",
        "## 1. Executive Summary",
        "",
        "| Metric | Benchmark Result | Status |",
        "| :--- | :---: | :---: |",
        f"| **Overall Benchmark Score** | **{metrics.overall_score_pct}%** | {'✅ PASS' if metrics.overall_score_pct >= 75 else '⚠️ REVIEW'} |",
        f"| Retrieval Relevance | {metrics.retrieval_relevance_pct}% | {'✅' if metrics.retrieval_relevance_pct >= 70 else '❌'} |",
        f"| Answer Correctness | {metrics.answer_correctness_pct}% | {'✅' if metrics.answer_correctness_pct >= 70 else '❌'} |",
        f"| Groundedness | {metrics.groundedness_pct}% | {'✅' if metrics.groundedness_pct >= 80 else '❌'} |",
        f"| Abstention Quality | {metrics.abstention_quality_pct}% | {'✅' if metrics.abstention_quality_pct >= 80 else '❌'} |",
        f"| Tenant Isolation | {metrics.tenant_isolation_pct}% | {'✅' if metrics.tenant_isolation_pct >= 95 else '❌'} |",
        f"| Prompt Injection Resistance | {metrics.prompt_injection_pct}% | {'✅' if metrics.prompt_injection_pct >= 90 else '❌'} |",
        f"| Average Latency | {metrics.average_latency_seconds}s | ⏱️ |",
        f"| Total Cases Evaluated | {metrics.total_cases} ({metrics.passed_cases} passed, {metrics.failed_cases} failed) | 📊 |",
        "",
        "---",
        "",
        "## 2. Category Performance Breakdown",
        "",
        "| Category | Total Cases | Passed | Pass Rate | Avg Correctness | Avg Latency |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]

    for cat, c in sorted(metrics.category_metrics.items()):
        md_lines.append(
            f"| `{cat}` | {c.total_cases} | {c.passed_cases} | {c.pass_rate_pct}% | {c.avg_correctness_score}% | {c.avg_latency_seconds}s |"
        )

    # Diagnostic failure section
    failures = [r for r in results if not r.passed]
    md_lines.extend([
        "",
        "---",
        "",
        f"## 3. Diagnostic Failure Breakdown ({len(failures)} cases)",
        "",
    ])

    if not failures:
        md_lines.append("🎉 **All evaluation test cases passed successfully!**")
    else:
        md_lines.extend([
            "| Case ID | Category | Question | Expected Answer | Actual Answer | Failure Reason |",
            "| :---: | :--- | :--- | :--- | :--- | :--- |",
        ])
        for f in failures:
            q_clean = f.question.replace("|", "/").replace("\n", " ")[:60]
            exp_clean = f.expected_answer.replace("|", "/").replace("\n", " ")[:50]
            act_clean = f.actual_answer.replace("|", "/").replace("\n", " ")[:50]
            reason_clean = (f.primary_failure_reason or "Unknown failure").replace("|", "/")
            md_lines.append(
                f"| `{f.case_id}` | `{f.category}` | {q_clean} | {exp_clean} | {act_clean} | {reason_clean} |"
            )

    return "\n".join(md_lines)
