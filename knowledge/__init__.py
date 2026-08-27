"""Knowledge Base Pipeline and Normalization Package for SupportBot AI."""

from knowledge.document_builder import (
    build_all_documents,
    build_business_document,
    build_catalog_document,
    build_faq_document,
    build_policy_documents,
    build_product_document,
)
from knowledge.document_loader import DocumentLoader
from knowledge.knowledge_manager import KnowledgeManager
from knowledge.metadata import (
    VALID_SOURCE_TYPES,
    create_document_metadata,
    validate_document_metadata,
)

__all__ = [
    "VALID_SOURCE_TYPES",
    "create_document_metadata",
    "validate_document_metadata",
    "build_business_document",
    "build_catalog_document",
    "build_product_document",
    "build_policy_documents",
    "build_faq_document",
    "build_all_documents",
    "DocumentLoader",
    "KnowledgeManager",
]

