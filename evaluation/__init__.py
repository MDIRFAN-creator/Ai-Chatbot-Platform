"""Evaluation subsystem for SupportBot AI platform."""

from evaluation.evaluators import (
    EvaluatorResult,
    evaluate_abstention_quality,
    evaluate_answer_correctness,
    evaluate_groundedness,
    evaluate_prompt_injection,
    evaluate_retrieval_relevance,
    evaluate_tenant_isolation,
)
from evaluation.metrics import (
    CaseEvaluationResult,
    CategoryMetricSummary,
    EvaluationSummaryMetrics,
    compute_evaluation_metrics,
)
from evaluation.report import (
    generate_dict_report,
    generate_json_report,
    generate_markdown_report,
)
from evaluation.runner import (
    EvaluationRunner,
    ensure_urbanthreads_seed_environment,
)
from evaluation.test_cases import (
    EvaluationCase,
    EvaluationDataset,
    Turn,
    load_evaluation_dataset,
)

__all__ = [
    "Turn",
    "EvaluationCase",
    "EvaluationDataset",
    "load_evaluation_dataset",
    "EvaluatorResult",
    "evaluate_retrieval_relevance",
    "evaluate_answer_correctness",
    "evaluate_groundedness",
    "evaluate_abstention_quality",
    "evaluate_prompt_injection",
    "evaluate_tenant_isolation",
    "CaseEvaluationResult",
    "CategoryMetricSummary",
    "EvaluationSummaryMetrics",
    "compute_evaluation_metrics",
    "generate_dict_report",
    "generate_json_report",
    "generate_markdown_report",
    "EvaluationRunner",
    "ensure_urbanthreads_seed_environment",
]
