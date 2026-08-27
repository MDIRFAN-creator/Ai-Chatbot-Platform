"""Evaluation Suite Runner for SupportBot AI.

Orchestrates batch execution of evaluation test cases against the RAG chatbot,
measuring performance across the 5 core benchmark pillars without contaminating
the production knowledge base or leaking test sessions.
"""

from typing import Callable, List, Optional
import time
import uuid

from core.database import DatabaseManager
from core.models import (
    AssistantSettingsCreate,
    BusinessCreate,
    FAQCreate,
    PolicyCreate,
    ProductCreate,
)
from evaluation.evaluators import (
    evaluate_abstention_quality,
    evaluate_answer_correctness,
    evaluate_groundedness,
    evaluate_prompt_injection,
    evaluate_retrieval_relevance,
    evaluate_tenant_isolation,
)
from evaluation.metrics import (
    CaseEvaluationResult,
    EvaluationSummaryMetrics,
    compute_evaluation_metrics,
)
from evaluation.test_cases import EvaluationCase, EvaluationDataset, load_evaluation_dataset
from knowledge.knowledge_manager import KnowledgeManager
from rag.vector_store import index_exists
from services.chatbot_service import ChatbotService, chatbot_service


def ensure_urbanthreads_seed_environment(
    db_manager: Optional[DatabaseManager] = None,
    business_id: str = "urbanthreads_001",
) -> str:
    """Ensure the target UrbanThreads business profile, products, policies, and vector index exist.

    This helper creates the standard UrbanThreads tenant environment in SQLite and builds
    its FAISS vector store if not already present, ensuring benchmark runs can execute.
    """
    db = db_manager or DatabaseManager()
    km = KnowledgeManager(db)

    existing_biz = db.get_business(business_id)
    if not existing_biz:
        db.create_business(
            BusinessCreate(
                business_id=business_id,
                name="UrbanThreads",
                description="An Indian D2C fashion brand focused on affordable contemporary streetwear and casual clothing.",
                industry="Fashion & Apparel",
                website="https://urbanthreads.example.com",
                contact_email="support@urbanthreads.example.com",
                contact_phone="+91-9876543210",
                location="Mumbai, India",
            )
        )
        db.create_or_update_assistant_settings(
            AssistantSettingsCreate(
                business_id=business_id,
                assistant_name="UrbanThreads Assistant",
                tone="friendly, stylish, and professional",
                welcome_message="Hi! Welcome to UrbanThreads. How can I help you today?",
            )
        )

        # Products
        db.create_product(
            ProductCreate(
                business_id=business_id,
                name="Oversized Black Hoodie",
                category="Hoodies",
                price=1499.0,
                currency="INR",
                sizes=["S", "M", "L", "XL"],
                colors=["Black"],
                availability="in_stock",
                returnable=True,
                description="400 GSM heavyweight premium cotton oversized black hoodie with double-stitched cuffs.",
            )
        )
        db.create_product(
            ProductCreate(
                business_id=business_id,
                name="Premium Oversized Hoodie",
                category="Hoodies",
                price=2299.0,
                currency="INR",
                sizes=["M", "L", "XL", "XXL"],
                colors=["Charcoal", "Sage Green"],
                availability="in_stock",
                returnable=True,
                description="Heavyweight luxury fleece hoodie featuring relaxed drop-shoulder silhouette.",
            )
        )
        db.create_product(
            ProductCreate(
                business_id=business_id,
                name="Bomber Jacket",
                category="Jackets",
                price=2499.0,
                currency="INR",
                sizes=["S", "M", "L"],
                colors=["Olive", "Black"],
                availability="in_stock",
                returnable=True,
                description="Water-resistant urban flight bomber jacket with ribbed collar and contrast lining.",
            )
        )
        db.create_product(
            ProductCreate(
                business_id=business_id,
                name="Limited Edition Graphic Tee",
                category="T-Shirts",
                price=999.0,
                currency="INR",
                sizes=["S", "M", "L"],
                colors=["White", "Vintage Black"],
                availability="in_stock",
                returnable=False,
                description="240 GSM single-run custom graphic tee. Final Sale item.",
            )
        )
        db.create_product(
            ProductCreate(
                business_id=business_id,
                name="Canvas Tote Bag",
                category="Accessories",
                price=399.0,
                currency="INR",
                colors=["Natural", "Black"],
                availability="in_stock",
                returnable=True,
                description="Durable 100% organic cotton canvas carryall tote.",
            )
        )

        # Policies
        db.create_policy(
            PolicyCreate(
                business_id=business_id,
                policy_type="shipping",
                content=(
                    "Standard shipping takes 3–5 business days across India. Express shipping takes 1–2 business days. "
                    "Free shipping applies on all orders above INR 1499. Orders below this threshold incur a standard shipping charge."
                ),
            )
        )
        db.create_policy(
            PolicyCreate(
                business_id=business_id,
                policy_type="payments",
                content=(
                    "We accept UPI, Credit/Debit Cards, Net Banking, and Cash on Delivery (COD) for eligible pin codes. "
                    "COD orders incur a standard handling fee of INR 49."
                ),
            )
        )
        db.create_policy(
            PolicyCreate(
                business_id=business_id,
                policy_type="returns",
                content=(
                    "Returns are accepted within 7 days of delivery for eligible unused products in original condition with tags intact. "
                    "Limited Edition items are Final Sale and non-returnable. Exchanges are available for size variations subject to stock availability."
                ),
            )
        )
        db.create_policy(
            PolicyCreate(
                business_id=business_id,
                policy_type="refunds",
                content=(
                    "Refunds are processed to the original payment method within 3–5 business days after the returned item passes quality inspection. "
                    "Shipping charges are generally non-refundable except for damaged, defective, or incorrectly delivered items."
                ),
            )
        )

        # FAQs
        db.create_faq(
            FAQCreate(
                business_id=business_id,
                question="Do you ship internationally?",
                answer="Currently, we only ship across India.",
            )
        )
        db.create_faq(
            FAQCreate(
                business_id=business_id,
                question="How can I track my order?",
                answer="You will receive a tracking link via SMS and email once your order ships.",
            )
        )

    # Rebuild vector store if index missing
    if not index_exists(business_id):
        km.build_knowledge_base(business_id)

    return business_id


class EvaluationRunner:
    """Executes evaluation suites against the chatbot service and grades outputs."""

    def __init__(
        self,
        service: Optional[ChatbotService] = None,
        db_manager: Optional[DatabaseManager] = None,
    ):
        self.service = service or chatbot_service
        self.db = db_manager or DatabaseManager()

    def run_case(
        self,
        case: EvaluationCase,
        business_id: str = "urbanthreads_001",
    ) -> CaseEvaluationResult:
        """Execute and grade an individual evaluation test case.

        Args:
            case: EvaluationCase specification.
            business_id: Target tenant ID (defaults to 'urbanthreads_001').

        Returns:
            CaseEvaluationResult containing responses, scores, and diagnostics.
        """
        # Dedicated evaluation session ID to prevent conversation contamination
        session_id = f"eval_sess_{case.id}_{uuid.uuid4().hex[:8]}"

        start_time = time.perf_counter()

        # Multi-turn prerequisite execution
        if case.type == "multi_turn" and case.turns and len(case.turns) > 1:
            # Execute prerequisite turns sequentially
            for turn in case.turns[:-1]:
                if turn.role == "user":
                    self.service.answer(
                        business_id=business_id,
                        session_id=session_id,
                        question=turn.content,
                    )
            final_question = case.turns[-1].content
        else:
            final_question = case.final_question

        # Execute final evaluated turn
        response = self.service.answer(
            business_id=business_id,
            session_id=session_id,
            question=final_question,
        )

        latency = round(time.perf_counter() - start_time, 3)

        # Run all evaluators
        retrieval_res = evaluate_retrieval_relevance(case, response)
        correctness_res = evaluate_answer_correctness(case, response)
        groundedness_res = evaluate_groundedness(case, response)
        abstention_res = evaluate_abstention_quality(case, response)
        injection_res = evaluate_prompt_injection(case, response)
        isolation_res = evaluate_tenant_isolation(case, response, expected_business_id=business_id)

        # Pass condition: all applicable evaluators must pass
        overall_passed = (
            retrieval_res.passed
            and correctness_res.passed
            and groundedness_res.passed
            and abstention_res.passed
            and injection_res.passed
            and isolation_res.passed
        )

        # Determine primary failure reason if any evaluator failed
        primary_reason = None
        if not overall_passed:
            if not retrieval_res.passed:
                primary_reason = f"Retrieval Failure: {retrieval_res.reason}"
            elif not correctness_res.passed:
                primary_reason = f"Answer Correctness Failure: {correctness_res.reason}"
            elif not groundedness_res.passed:
                primary_reason = f"Groundedness Failure: {groundedness_res.reason}"
            elif not abstention_res.passed:
                primary_reason = f"Abstention Failure: {abstention_res.reason}"
            elif not injection_res.passed:
                primary_reason = f"Prompt Injection Failure: {injection_res.reason}"
            elif not isolation_res.passed:
                primary_reason = f"Tenant Isolation Failure: {isolation_res.reason}"

        return CaseEvaluationResult(
            case_id=case.id,
            category=case.category,
            question=final_question,
            expected_answer=case.expected_answer,
            actual_answer=response.answer,
            retrieved_documents=response.retrieved_documents,
            fallback_triggered=response.fallback_triggered,
            latency_seconds=latency,
            retrieval_result=retrieval_res,
            correctness_result=correctness_res,
            groundedness_result=groundedness_res,
            abstention_result=abstention_res,
            injection_result=injection_res,
            isolation_result=isolation_res,
            passed=overall_passed,
            primary_failure_reason=primary_reason,
            details=response.metadata,
        )

    def run_suite(
        self,
        dataset: Optional[EvaluationDataset] = None,
        category: Optional[str] = None,
        case_type: Optional[str] = None,
        business_id: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> tuple[EvaluationSummaryMetrics, List[CaseEvaluationResult]]:
        """Run an automated evaluation suite against the specified dataset.

        Args:
            dataset: EvaluationDataset instance (loads standard dataset if None).
            category: Optional category filter.
            case_type: Optional turn type filter.
            business_id: Target tenant ID (defaults to dataset.business_id or 'urbanthreads_001').
            progress_callback: Optional callback receiving (current_index, total_cases, current_case_id).

        Returns:
            Tuple of (EvaluationSummaryMetrics, List[CaseEvaluationResult]).
        """
        ds = dataset or load_evaluation_dataset(category=category, case_type=case_type)
        target_bid = business_id or ds.business_id

        # Verify or initialize UrbanThreads seed environment if evaluating urbanthreads_001
        if target_bid == "urbanthreads_001":
            ensure_urbanthreads_seed_environment(self.db, target_bid)

        results: List[CaseEvaluationResult] = []
        total = len(ds.cases)

        for idx, case in enumerate(ds.cases, start=1):
            if progress_callback:
                progress_callback(idx, total, case.id)

            case_res = self.run_case(case, business_id=target_bid)
            results.append(case_res)

        metrics = compute_evaluation_metrics(results)
        return metrics, results
