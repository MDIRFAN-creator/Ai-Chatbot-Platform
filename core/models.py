"""Domain models and Pydantic validation schemas for SupportBot AI.

This module defines data structures representing all 8 core database entities
(businesses, assistant_settings, products, policies, faqs, knowledge_documents,
conversations, messages) along with their creation and update schemas.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


def get_utc_now_iso() -> str:
    """Return the current UTC datetime in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


# =====================================================================
# 1. BUSINESS MODELS
# =====================================================================

class BusinessBase(BaseModel):
    """Base fields for a business profile."""
    name: str = Field(..., min_length=1, description="Business name")
    description: Optional[str] = Field(None, description="Business overview/description")
    industry: Optional[str] = Field(None, description="Industry or niche")
    website: Optional[str] = Field(None, description="Business website URL")
    contact_email: Optional[str] = Field(None, description="Customer contact email")
    contact_phone: Optional[str] = Field(None, description="Customer contact phone")
    location: Optional[str] = Field(None, description="Physical address or headquarters")


class BusinessCreate(BusinessBase):
    """Schema for creating a new business."""
    business_id: Optional[str] = Field(None, description="Optional custom business ID; auto-generated if omitted")


class BusinessUpdate(BaseModel):
    """Schema for updating an existing business."""
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    location: Optional[str] = None


class Business(BusinessBase):
    """Complete Business domain model representing the database record."""
    business_id: str
    created_at: str = Field(default_factory=get_utc_now_iso)
    updated_at: str = Field(default_factory=get_utc_now_iso)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =====================================================================
# 2. ASSISTANT SETTINGS MODELS
# =====================================================================

class AssistantSettingsBase(BaseModel):
    """Base fields for assistant configuration."""
    assistant_name: str = Field(..., min_length=1, description="Name of the AI assistant")
    tone: Optional[str] = Field("professional and friendly", description="Personality / tone of the assistant")
    welcome_message: Optional[str] = Field(None, description="Initial greeting message shown in chat")


class AssistantSettingsCreate(AssistantSettingsBase):
    """Schema for creating assistant settings."""
    assistant_id: Optional[str] = None
    business_id: str = Field(..., min_length=1, description="Associated business ID")


class AssistantSettingsUpdate(BaseModel):
    """Schema for updating assistant settings."""
    assistant_name: Optional[str] = Field(None, min_length=1)
    tone: Optional[str] = None
    welcome_message: Optional[str] = None


class AssistantSettings(AssistantSettingsBase):
    """Complete AssistantSettings domain model."""
    assistant_id: str
    business_id: str
    created_at: str = Field(default_factory=get_utc_now_iso)
    updated_at: str = Field(default_factory=get_utc_now_iso)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =====================================================================
# 3. PRODUCT MODELS
# =====================================================================

class ProductBase(BaseModel):
    """Base fields for a product."""
    name: str = Field(..., min_length=1, description="Product title / name")
    description: Optional[str] = Field(None, description="Detailed product description")
    price: Optional[float] = Field(None, ge=0.0, description="Product price")
    currency: Optional[str] = Field("USD", description="Price currency code")
    category: Optional[str] = Field(None, description="Product category / collection")
    sizes: List[str] = Field(default_factory=list, description="Available product sizes")
    colors: List[str] = Field(default_factory=list, description="Available product colors")
    availability: Optional[str] = Field("in_stock", description="Inventory status (e.g., in_stock, out_of_stock)")
    returnable: bool = Field(True, description="Whether this product is eligible for returns")
    product_url: Optional[str] = Field(None, description="Link to product page on store")


class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    product_id: Optional[str] = None
    business_id: str = Field(..., min_length=1, description="Associated business ID")


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = None
    category: Optional[str] = None
    sizes: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    availability: Optional[str] = None
    returnable: Optional[bool] = None
    product_url: Optional[str] = None


class Product(ProductBase):
    """Complete Product domain model."""
    product_id: str
    business_id: str
    created_at: str = Field(default_factory=get_utc_now_iso)
    updated_at: str = Field(default_factory=get_utc_now_iso)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =====================================================================
# 4. POLICY MODELS
# =====================================================================

class PolicyBase(BaseModel):
    """Base fields for a business policy."""
    policy_type: str = Field(..., min_length=1, description="Type of policy (e.g. shipping, returns, refunds, payment, sizing)")
    content: str = Field(..., min_length=1, description="Policy text / rules")

    @field_validator("policy_type")
    @classmethod
    def normalize_policy_type(cls, v: str) -> str:
        """Normalize policy type to lowercase stripped string."""
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("policy_type cannot be blank")
        return cleaned


class PolicyCreate(PolicyBase):
    """Schema for creating a policy."""
    policy_id: Optional[str] = None
    business_id: str = Field(..., min_length=1, description="Associated business ID")


class PolicyUpdate(BaseModel):
    """Schema for updating a policy."""
    policy_type: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)

    @field_validator("policy_type")
    @classmethod
    def normalize_policy_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip().lower()
            if not cleaned:
                raise ValueError("policy_type cannot be blank")
            return cleaned
        return v


class Policy(PolicyBase):
    """Complete Policy domain model."""
    policy_id: str
    business_id: str
    created_at: str = Field(default_factory=get_utc_now_iso)
    updated_at: str = Field(default_factory=get_utc_now_iso)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =====================================================================
# 5. FAQ MODELS
# =====================================================================

class FAQBase(BaseModel):
    """Base fields for an FAQ item."""
    question: str = Field(..., min_length=1, description="Customer question")
    answer: str = Field(..., min_length=1, description="Business answer")


class FAQCreate(FAQBase):
    """Schema for creating an FAQ."""
    faq_id: Optional[str] = None
    business_id: str = Field(..., min_length=1, description="Associated business ID")


class FAQUpdate(BaseModel):
    """Schema for updating an FAQ."""
    question: Optional[str] = Field(None, min_length=1)
    answer: Optional[str] = Field(None, min_length=1)


class FAQ(FAQBase):
    """Complete FAQ domain model."""
    faq_id: str
    business_id: str
    created_at: str = Field(default_factory=get_utc_now_iso)
    updated_at: str = Field(default_factory=get_utc_now_iso)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =====================================================================
# 6. KNOWLEDGE DOCUMENT MODELS
# =====================================================================

class KnowledgeDocumentBase(BaseModel):
    """Base fields for a knowledge document."""
    source_type: str = Field(..., min_length=1, description="Source type (business, product, policy, faq)")
    source_id: str = Field(..., min_length=1, description="ID of the source entity")
    content: str = Field(..., min_length=1, description="Normalized text representation for RAG")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")


class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    """Schema for creating a knowledge document."""
    knowledge_id: Optional[str] = None
    business_id: str = Field(..., min_length=1, description="Associated business ID")


class KnowledgeDocumentUpdate(BaseModel):
    """Schema for updating a knowledge document."""
    source_type: Optional[str] = Field(None, min_length=1)
    source_id: Optional[str] = Field(None, min_length=1)
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeDocument(KnowledgeDocumentBase):
    """Complete KnowledgeDocument domain model."""
    knowledge_id: str
    business_id: str
    created_at: str = Field(default_factory=get_utc_now_iso)
    updated_at: str = Field(default_factory=get_utc_now_iso)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =====================================================================
# 7. CONVERSATION MODELS
# =====================================================================

class ConversationBase(BaseModel):
    """Base fields for a chat conversation."""
    session_id: str = Field(..., min_length=1, description="Client or browser session ID")


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""
    conversation_id: Optional[str] = None
    business_id: str = Field(..., min_length=1, description="Associated business ID")


class Conversation(ConversationBase):
    """Complete Conversation domain model."""
    conversation_id: str
    business_id: str
    created_at: str = Field(default_factory=get_utc_now_iso)
    updated_at: str = Field(default_factory=get_utc_now_iso)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# =====================================================================
# 8. MESSAGE MODELS
# =====================================================================

MessageRole = Literal["user", "assistant"]


class MessageBase(BaseModel):
    """Base fields for a single chat message."""
    role: MessageRole = Field(..., description="Message sender role (user or assistant)")
    content: str = Field(..., min_length=1, description="Message text content")


class MessageCreate(MessageBase):
    """Schema for creating a message."""
    message_id: Optional[str] = None
    conversation_id: str = Field(..., min_length=1, description="Parent conversation ID")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of message creation")


class Message(MessageBase):
    """Complete Message domain model."""
    message_id: str
    conversation_id: str
    timestamp: str = Field(default_factory=get_utc_now_iso)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
