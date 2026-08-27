"""Form helpers and input validation formatting for Streamlit pages."""

from typing import Any, List
from pydantic import ValidationError
import streamlit as st


def parse_comma_separated(value: str) -> List[str]:
    """Parse comma-separated string into a cleaned list of non-empty strings."""
    if not value or not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def handle_validation_error(err: ValidationError) -> None:
    """Format and display Pydantic validation errors clearly in the UI."""
    error_messages = []
    for error in err.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        msg = error["msg"]
        error_messages.append(f"**{field}**: {msg}")
    st.error("Validation Error:\n\n" + "\n\n".join(f"- {m}" for m in error_messages))
