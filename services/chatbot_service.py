"""Chatbot Service layer for SupportBot AI.

Provides the application-facing interface for customer-support question answering,
wrapping the RAG orchestrator chain.
"""

from typing import Optional
from core.database import DatabaseManager
from rag.chain import RAGChain, RAGResponse


class ChatbotService:
    """Service layer coordinating question-answering across tenants."""

    def __init__(
        self,
        rag_chain: Optional[RAGChain] = None,
        db_manager: Optional[DatabaseManager] = None,
    ):
        self.db = db_manager or DatabaseManager()
        self.chain = rag_chain or RAGChain(self.db)

    def answer(
        self,
        business_id: str,
        session_id: str,
        question: str,
        top_k: Optional[int] = None,
    ) -> RAGResponse:
        """Process a customer question and return a structured RAG response.

        Args:
            business_id: Business tenant identifier.
            session_id: Client/browser session identifier.
            question: Customer question string.
            top_k: Optional custom retrieval top-k count.

        Returns:
            RAGResponse object containing answer, retrieved documents, and metadata.
        """
        return self.chain.answer(
            business_id=business_id,
            session_id=session_id,
            question=question,
            top_k=top_k,
        )


# Global singleton service instance
chatbot_service = ChatbotService()
