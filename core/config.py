"""Centralized Application Configuration for SupportBot AI.

This module loads environment variables and provides a structured configuration
for all application layers (UI, Core, Knowledge, RAG, Services, Evaluation).
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    # Load .env file from project root if present
    load_dotenv()
except ImportError:
    pass

# Base directory of the repository
BASE_DIR: Path = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration settings."""

    # Application Environment
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    debug: bool = field(
        default_factory=lambda: os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
    )

    # LLM Configuration
    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "gemini")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gemini-2.5-flash")
    )
    gemini_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )

    # Embedding Configuration
    embedding_provider: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "huggingface_local")
    )
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )

    # Database Configuration
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "sqlite:///data/supportbot.db"
        )
    )
    database_path: Path = field(
        default_factory=lambda: BASE_DIR / "data" / "supportbot.db"
    )

    # Retrieval Configuration
    retrieval_top_k: int = field(
        default_factory=lambda: int(os.getenv("RETRIEVAL_TOP_K", "5"))
    )

    # Storage Paths
    vector_store_dir: Path = field(
        default_factory=lambda: BASE_DIR / "vectorstore"
    )
    evaluation_dataset_path: Path = field(
        default_factory=lambda: BASE_DIR
        / "data"
        / "evaluation"
        / "urbanthreads_evaluation.json"
    )

    @property
    def is_gemini_configured(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.gemini_api_key and self.gemini_api_key.strip())


# Global configuration instance
config = AppConfig()


def get_config() -> AppConfig:
    """Retrieve the current application configuration instance."""
    return config
