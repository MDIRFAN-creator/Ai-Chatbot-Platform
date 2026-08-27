"""Request and Response Pydantic schemas for the SupportBot AI HTTP Chat API."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ChatApiRequest(BaseModel):
    """Incoming chat message request schema for the HTTP API."""
    business_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique identifier of the target business tenant",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Unique session ID for conversation continuity",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Customer text message or query",
    )

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class ChatApiResponse(BaseModel):
    """Outgoing chat response schema from the HTTP API."""
    answer: str = Field(..., description="Assistant response text")
    business_id: str = Field(..., description="Business tenant ID")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    fallback_triggered: bool = Field(
        default=False,
        description="Indicates whether safe fallback was triggered",
    )

    model_config = ConfigDict(extra="ignore")


class HealthResponse(BaseModel):
    """API health status response schema."""
    status: str = Field(default="healthy")
    service: str = Field(default="SupportBot AI Chat API")
    version: str = Field(default="1.0.0")

    model_config = ConfigDict(extra="ignore")


class ErrorResponse(BaseModel):
    """Standardized error response schema."""
    error: str = Field(..., description="High-level error category or message")
    detail: Optional[str] = Field(None, description="Safe details regarding the error")

    model_config = ConfigDict(extra="ignore")
