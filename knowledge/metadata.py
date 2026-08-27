"""Centralized metadata creation and validation for SupportBot AI knowledge documents.

Every generated knowledge document in LangChain and persisted record in SQLite
must carry standardized, validated metadata enforcing tenant isolation.
"""

from typing import Any, Dict, List, Set

VALID_SOURCE_TYPES: Set[str] = {"business", "product", "policy", "faq"}


def validate_document_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that required metadata fields exist and conform to standards.

    Required fields:
        - business_id (str, non-empty)
        - source_type (str, in VALID_SOURCE_TYPES)
        - source_id (str, non-empty)

    Raises:
        ValueError: If any mandatory field is missing, empty, or invalid.
    """
    if not isinstance(metadata, dict):
        raise ValueError(f"Metadata must be a dict, got {type(metadata).__name__}")

    business_id = metadata.get("business_id")
    if not business_id or not isinstance(business_id, str) or not business_id.strip():
        raise ValueError("Missing or invalid required metadata field: 'business_id'")

    source_type = metadata.get("source_type")
    if not source_type or not isinstance(source_type, str) or source_type not in VALID_SOURCE_TYPES:
        raise ValueError(
            f"Invalid 'source_type': {source_type!r}. Must be one of {sorted(VALID_SOURCE_TYPES)}"
        )

    source_id = metadata.get("source_id")
    if not source_id or not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("Missing or invalid required metadata field: 'source_id'")

    return metadata


def create_document_metadata(
    business_id: str,
    source_type: str,
    source_id: str,
    **extra_fields: Any,
) -> Dict[str, Any]:
    """Construct and validate standardized document metadata.

    Args:
        business_id: The unique identifier of the business tenant.
        source_type: The source entity type ("business", "product", "policy", "faq").
        source_id: The identifier of the source entity.
        **extra_fields: Additional domain-specific metadata (e.g., category, policy_type, chunk_index).

    Returns:
        Validated metadata dictionary suitable for LangChain Document and SQLite storage.
    """
    meta: Dict[str, Any] = {
        "business_id": business_id.strip() if isinstance(business_id, str) else business_id,
        "source_type": source_type.strip() if isinstance(source_type, str) else source_type,
        "source_id": source_id.strip() if isinstance(source_id, str) else source_id,
    }

    # Add extra non-null fields
    for k, v in extra_fields.items():
        if v is not None:
            meta[k] = v

    return validate_document_metadata(meta)
