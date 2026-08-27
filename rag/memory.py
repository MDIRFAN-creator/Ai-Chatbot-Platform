"""Short-Term Conversation Memory Module for SupportBot AI.

Provides bounded, tenant-isolated message history retrieval from SQLite
for conversational continuity without replacing authoritative RAG retrieval.
"""

from typing import List, Optional
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from core.config import get_config
from core.database import DatabaseManager
from core.models import Message


class ConversationMemory:
    """Manages short-term dialogue context for a single tenant session."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def get_recent_messages(
        self,
        conversation_id: str,
        business_id: str,
        max_turns: Optional[int] = None,
    ) -> List[Message]:
        """Retrieve recent message history bounded by turn limit.

        Args:
            conversation_id: Unique conversation identifier.
            business_id: Unique business tenant identifier for isolation verification.
            max_turns: Maximum number of dialogue turns (1 turn = 1 user + 1 assistant msg).
                       Defaults to config.max_conversation_turns.

        Returns:
            List of Message domain models ordered chronologically (oldest to newest).
        """
        if not conversation_id or not business_id:
            return []

        cfg = get_config()
        turns = max_turns if max_turns is not None and max_turns > 0 else cfg.max_conversation_turns
        max_messages = turns * 2

        all_messages = self.db.get_messages_by_conversation(
            conversation_id=conversation_id,
            business_id=business_id,
        )

        if not all_messages:
            return []

        # Return only the most recent N messages
        return all_messages[-max_messages:]

    def get_langchain_messages(
        self,
        conversation_id: str,
        business_id: str,
        max_turns: Optional[int] = None,
    ) -> List[BaseMessage]:
        """Retrieve recent messages as LangChain HumanMessage / AIMessage objects."""
        messages = self.get_recent_messages(conversation_id, business_id, max_turns=max_turns)
        lc_messages: List[BaseMessage] = []
        for msg in messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
        return lc_messages
