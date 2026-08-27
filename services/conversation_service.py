"""Conversation Service for SupportBot AI.

Manages chat session lifecycle, conversation retrieval, and message persistence
strictly within tenant boundaries.
"""

from typing import List, Optional
from core.database import DatabaseManager
from core.models import Conversation, ConversationCreate, Message, MessageCreate


class ConversationService:
    """Service layer for tenant-isolated conversations and message histories."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def get_or_create_conversation(
        self,
        business_id: str,
        session_id: str,
    ) -> Conversation:
        """Retrieve existing active conversation for session_id or create a new one.

        Args:
            business_id: Business tenant identifier.
            session_id: Client/browser session identifier.

        Returns:
            Conversation domain model.
        """
        if not business_id or not session_id:
            raise ValueError("Both business_id and session_id are required.")

        clean_bid = business_id.strip()
        clean_sid = session_id.strip()

        existing = self.db.get_conversation_by_session(clean_bid, clean_sid)
        if existing:
            return existing

        return self.db.create_conversation(
            ConversationCreate(business_id=clean_bid, session_id=clean_sid)
        )

    def add_user_message(
        self,
        business_id: str,
        conversation_id: str,
        content: str,
    ) -> Message:
        """Append a user message to a tenant conversation."""
        if not content or not content.strip():
            raise ValueError("Message content cannot be empty.")

        return self.db.create_message(
            MessageCreate(
                conversation_id=conversation_id,
                role="user",
                content=content.strip(),
            ),
            business_id=business_id,
        )

    def add_assistant_message(
        self,
        business_id: str,
        conversation_id: str,
        content: str,
    ) -> Message:
        """Append an assistant message to a tenant conversation."""
        if not content or not content.strip():
            raise ValueError("Message content cannot be empty.")

        return self.db.create_message(
            MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                content=content.strip(),
            ),
            business_id=business_id,
        )

    def get_conversation_messages(
        self,
        business_id: str,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """Retrieve messages for a conversation strictly owned by business_id."""
        messages = self.db.get_messages_by_conversation(
            conversation_id=conversation_id,
            business_id=business_id,
        )
        if limit is not None and limit > 0:
            return messages[-limit:]
        return messages

    def get_conversation(
        self,
        business_id: str,
        conversation_id: str,
    ) -> Optional[Conversation]:
        """Retrieve a conversation ensuring tenant ownership."""
        return self.db.get_conversation(conversation_id, business_id)

    def get_conversations_by_business(self, business_id: str) -> List[Conversation]:
        """Retrieve all conversations belonging to a business."""
        return self.db.get_conversations_by_business(business_id)

    def delete_conversation(self, business_id: str, conversation_id: str) -> bool:
        """Delete a conversation with business verification."""
        return self.db.delete_conversation(conversation_id, business_id)


# Global singleton service instance
conversation_service = ConversationService()
