"""Metrics Calculation Engine for SupportBot AI Evaluation Pipeline.

Computes benchmark percentage rates for:
1. Retrieval Relevance (%)
2. Answer Correctness (%)
3. Groundedness (%)
4. Abstention Quality (%)
5. Tenant Isolation (%)
6. Prompt Injection Resistance (%)
7. Overall Benchmark Score (%)
plus category-level aggregate statistics.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from langchain_core.documents import Document

from evaluation.evaluators import EvaluatorResult


@dataclass
class CaseEvaluationResult:
    """Complete evaluation results and diagnostics for a single evaluation case."""
    case_id: str
    category: str
    question: str
    expected_answer: str
    actual_answer: str
    retrieved_documents: List[Document]
    fallback_triggered: bool
    latency_seconds: float
    retrieval_result: EvaluatorResult
    correctness_result: EvaluatorResult
    groundedness_result: EvaluatorResult
    abstention_result: EvaluatorResult
    injection_result: EvaluatorResult
    isolation_result: EvaluatorResult
    passed: bool
    primary_failure_reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CategoryMetricSummary:
    """Aggregate metric scores for a specific evaluation category."""
    category: str
    total_cases: int
    passed_cases: int
    pass_rate_pct: float
    avg_correctness_score: float
    avg_latency_seconds: float


@dataclass
class EvaluationSummaryMetrics:
    """High-level summary metric scores for the entire evaluation run."""
    total_cases: int
    passed_cases: int
    failed_cases: int
    overall_score_pct: float
    retrieval_relevance_pct: float
    answer_correctness_pct: float
    groundedness_pct: float
    abstention_quality_pct: float
    tenant_isolation_pct: float
    prompt_injection_pct: float
    average_latency_seconds: float
    category_metrics: Dict[str, CategoryMetricSummary] = field(default_factory=dict)


def compute_evaluation_metrics(
    results: List[CaseEvaluationResult],
) -> EvaluationSummaryMetrics:
    """Compute aggregate benchmark scores and category breakdowns from case results.

    Args:
        results: List of CaseEvaluationResult objects.

    Returns:
        EvaluationSummaryMetrics dataclass containing all calculated rates.
    """
    total = len(results)
    if total == 0:
        return EvaluationSummaryMetrics(
            total_cases=0,
            passed_cases=0,
            failed_cases=0,
            overall_score_pct=0.0,
            retrieval_relevance_pct=0.0,
            answer_correctness_pct=0.0,
            groundedness_pct=0.0,
            abstention_quality_pct=0.0,
            tenant_isolation_pct=0.0,
            prompt_injection_pct=0.0,
            average_latency_seconds=0.0,
        )

    passed_count = sum(1 for r in results if r.passed)
    failed_count = total - passed_count

    # Sum scores
    retrieval_sum = sum(r.retrieval_result.score for r in results)
    correctness_sum = sum(r.correctness_result.score for r in results)
    groundedness_sum = sum(r.groundedness_result.score for r in results)
    abstention_sum = sum(r.abstention_result.score for r in results)
    isolation_sum = sum(r.isolation_result.score for r in results)
    injection_sum = sum(r.injection_result.score for r in results)
    latency_sum = sum(r.latency_seconds for r in results)

    # Rates (0.0 to 100.0)
    retrieval_pct = round((retrieval_sum / total) * 100.0, 2)
    correctness_pct = round((correctness_sum / total) * 100.0, 2)
    groundedness_pct = round((groundedness_sum / total) * 100.0, 2)
    abstention_pct = round((abstention_sum / total) * 100.0, 2)
    isolation_pct = round((isolation_sum / total) * 100.0, 2)
    injection_pct = round((injection_sum / total) * 100.0, 2)
    avg_latency = round(latency_sum / total, 3)

    # Overall benchmark score (weighted average across the 5 core pillars)
    core_scores = [retrieval_pct, correctness_pct, groundedness_pct, abstention_pct, isolation_pct]
    overall_pct = round(sum(core_scores) / len(core_scores), 2)

    # Category breakdown
    categories: Dict[str, List[CaseEvaluationResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    category_summaries: Dict[str, CategoryMetricSummary] = {}
    for cat, cat_results in categories.items():
        cat_total = len(cat_results)
        cat_passed = sum(1 for cr in cat_results if cr.passed)
        cat_pass_rate = round((cat_passed / cat_total) * 100.0, 2)
        cat_avg_corr = round((sum(cr.correctness_result.score for cr in cat_results) / cat_total) * 100.0, 2)
        cat_avg_lat = round(sum(cr.latency_seconds for cr in cat_results) / cat_total, 3)

        category_summaries[cat] = CategoryMetricSummary(
            category=cat,
            total_cases=cat_total,
            passed_cases=cat_passed,
            pass_rate_pct=cat_pass_rate,
            avg_correctness_score=cat_avg_corr,
            avg_latency_seconds=cat_avg_lat,
        )

    return EvaluationSummaryMetrics(
        total_cases=total,
        passed_cases=passed_count,
        failed_cases=failed_count,
        overall_score_pct=overall_pct,
        retrieval_relevance_pct=retrieval_pct,
        answer_correctness_pct=correctness_pct,
        groundedness_pct=groundedness_pct,
        abstention_quality_pct=abstention_pct,
        tenant_isolation_pct=isolation_pct,
        prompt_injection_pct=injection_pct,
        average_latency_seconds=avg_latency,
        category_metrics=category_summaries,
    )
