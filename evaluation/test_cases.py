"""Evaluation Test Cases and Dataset Loader for SupportBot AI.

Provides Pydantic schemas and deterministic JSON parsing for the developer-controlled
evaluation dataset at `data/evaluation/urbanthreads_evaluation.json`.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from core.config import get_config


class Turn(BaseModel):
    """A single conversational dialogue turn in a multi-turn evaluation case."""
    role: str = Field(..., description="Sender role: 'user', 'assistant', or 'assistant_expected'")
    content: str = Field(..., min_length=1, description="Text content of the message")

    model_config = ConfigDict(extra="ignore")


class EvaluationCase(BaseModel):
    """Schema representing an individual RAG evaluation test case."""
    id: str = Field(..., description="Unique case identifier (e.g. 'E001')")
    category: str = Field(..., description="Evaluation category")
    type: Literal["single_turn", "multi_turn"] = Field(
        default="single_turn", description="Turn structure of the test case"
    )
    question: Optional[str] = Field(
        None, description="Direct user question for single-turn test cases"
    )
    turns: Optional[List[Turn]] = Field(
        None, description="Prerequisite and evaluated dialogue turns for multi-turn cases"
    )
    expected_answer: str = Field(
        ..., description="Reference expected ground-truth answer or behavior description"
    )
    expected_sources: Optional[List[str]] = Field(
        None, description="Optional expected source types (e.g. ['product', 'policy'])"
    )

    model_config = ConfigDict(extra="ignore")

    @property
    def final_question(self) -> str:
        """Extract the final prompt/question string for evaluation."""
        if self.question and self.question.strip():
            return self.question.strip()
        if self.turns and len(self.turns) > 0:
            # Find the last turn with role == 'user'
            for t in reversed(self.turns):
                if t.role == "user":
                    return t.content.strip()
            return self.turns[-1].content.strip()
        return ""


class EvaluationDataset(BaseModel):
    """Complete container model for the evaluation dataset."""
    dataset_name: str
    business_id: str
    version: str
    total_cases: int
    evaluation_goals: List[str] = Field(default_factory=list)
    cases: List[EvaluationCase] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


def load_evaluation_dataset(
    dataset_path: Optional[Path] = None,
    category: Optional[str] = None,
    case_type: Optional[str] = None,
) -> EvaluationDataset:
    """Load and validate the evaluation dataset from JSON.

    Args:
        dataset_path: Optional file path override (defaults to config.evaluation_dataset_path).
        category: Optional category filter string.
        case_type: Optional turn type filter ('single_turn' or 'multi_turn').

    Returns:
        Validated EvaluationDataset instance.

    Raises:
        FileNotFoundError: If the evaluation JSON file does not exist.
        ValueError: If JSON content is malformed or schema validation fails.
    """
    path = dataset_path or get_config().evaluation_dataset_path
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset file not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in evaluation dataset {path}: {exc}") from exc

    try:
        dataset = EvaluationDataset.model_validate(raw_data)
    except Exception as exc:
        raise ValueError(f"Schema validation failed for evaluation dataset {path}: {exc}") from exc

    # Apply optional filtering
    filtered_cases = dataset.cases
    if category and category.strip():
        filtered_cases = [c for c in filtered_cases if c.category.lower() == category.strip().lower()]
    if case_type and case_type.strip():
        filtered_cases = [c for c in filtered_cases if c.type.lower() == case_type.strip().lower()]

    return EvaluationDataset(
        dataset_name=dataset.dataset_name,
        business_id=dataset.business_id,
        version=dataset.version,
        total_cases=len(filtered_cases),
        evaluation_goals=dataset.evaluation_goals,
        cases=filtered_cases,
    )
