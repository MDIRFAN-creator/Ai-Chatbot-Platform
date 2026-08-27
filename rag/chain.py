"""RAG Orchestrator Chain for SupportBot AI.

Coordinates the complete question-answering workflow:
1. Business validation & context loading
2. Session and conversation management
3. Security & prompt-injection guardrails
4. Business-scoped vector retrieval
5. Context sufficiency & grounding evaluation
6. Deterministic safe fallback on missing context
7. Grounded prompt assembly
8. Gemini LLM generation
9. Conversation message persistence
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel

from core.database import DatabaseManager
from core.models import AssistantSettings, Business, ConversationCreate, MessageCreate
from rag.guardrails import (
    check_prompt_injection,
    check_retrieval_grounding,
    generate_fallback_response,
    generate_injection_refusal_response,
    sanitize_response,
)
from rag.llm import get_llm
from rag.memory import ConversationMemory
from rag.prompts import build_rag_prompt_messages
from rag.retriever import retrieve


@dataclass
class RAGResponse:
    """Structured response container from the RAG pipeline."""
    answer: str
    business_id: str
    session_id: str
    conversation_id: str
    retrieved_documents: List[Document] = field(default_factory=list)
    fallback_triggered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGChain:
    """End-to-end RAG orchestrator for tenant-scoped customer support."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        memory: Optional[ConversationMemory] = None,
        llm: Optional[BaseChatModel] = None,
    ):
        self.db = db_manager or DatabaseManager()
        self.memory = memory or ConversationMemory(self.db)
        self._llm = llm

    def _get_llm(self) -> BaseChatModel:
        """Return configured LLM or injected mock."""
        if self._llm is not None:
            return self._llm
        return get_llm()

    def _get_or_create_conversation(self, business_id: str, session_id: str):
        existing = self.db.get_conversation_by_session(business_id, session_id)
        if existing:
            return existing
        return self.db.create_conversation(
            ConversationCreate(business_id=business_id, session_id=session_id)
        )

    def _add_message(self, business_id: str, conversation_id: str, role: str, content: str):
        return self.db.create_message(
            MessageCreate(conversation_id=conversation_id, role=role, content=content),  # type: ignore[arg-type]
            business_id=business_id,
        )

    def answer(
        self,
        business_id: str,
        session_id: str,
        question: str,
        top_k: Optional[int] = None,
    ) -> RAGResponse:
        """Process a customer query and generate a grounded, conversational response.

        Args:
            business_id: Business tenant identifier.
            session_id: Client session identifier.
            question: Customer question string.
            top_k: Optional retrieval top-k override.

        Returns:
            Structured RAGResponse object.
        """
        if not business_id or not isinstance(business_id, str) or not business_id.strip():
            raise ValueError("A valid, non-empty business_id is required.")
        if not session_id or not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("A valid, non-empty session_id is required.")

        clean_bid = business_id.strip()
        clean_sid = session_id.strip()
        clean_question = question.strip() if question else ""

        # 1. Load Business Context & Assistant Settings
        business: Optional[Business] = self.db.get_business(clean_bid)
        assistant: Optional[AssistantSettings] = self.db.get_assistant_settings(clean_bid)

        # 2. Get or create conversation session
        conversation = self._get_or_create_conversation(clean_bid, clean_sid)
        conv_id = conversation.conversation_id

        # Handle empty question
        if not clean_question:
            empty_ans = "Please ask a question so I can assist you."
            return RAGResponse(
                answer=empty_ans,
                business_id=clean_bid,
                session_id=clean_sid,
                conversation_id=conv_id,
                fallback_triggered=True,
            )

        # 3. Security Guardrail: Prompt Injection Detection
        if check_prompt_injection(clean_question):
            refusal = generate_injection_refusal_response(business)
            # Record turn in conversation
            self._add_message(clean_bid, conv_id, "user", clean_question)
            self._add_message(clean_bid, conv_id, "assistant", refusal)
            return RAGResponse(
                answer=refusal,
                business_id=clean_bid,
                session_id=clean_sid,
                conversation_id=conv_id,
                fallback_triggered=True,
                metadata={"reason": "prompt_injection_blocked"},
            )

        # 4. Perform Business-Scoped Vector Retrieval
        retrieved_docs = retrieve(
            query=clean_question,
            business_id=clean_bid,
            top_k=top_k,
        )

        # 5. Grounding Guardrail: Check retrieval sufficiency
        is_grounded = check_retrieval_grounding(retrieved_docs, clean_question)

        if not is_grounded:
            # Trigger safe deterministic abstention
            fallback_ans = generate_fallback_response(business, clean_question)
            self._add_message(clean_bid, conv_id, "user", clean_question)
            self._add_message(clean_bid, conv_id, "assistant", fallback_ans)
            return RAGResponse(
                answer=fallback_ans,
                business_id=clean_bid,
                session_id=clean_sid,
                conversation_id=conv_id,
                retrieved_documents=retrieved_docs,
                fallback_triggered=True,
                metadata={"reason": "insufficient_retrieval_context"},
            )

        # 6. Load Recent Conversation History (bounded for continuity)
        recent_messages = self.memory.get_recent_messages(
            conversation_id=conv_id,
            business_id=clean_bid,
        )

        # 7. Construct Grounded Prompt Messages
        prompt_messages = build_rag_prompt_messages(
            business=business,
            assistant=assistant,
            documents=retrieved_docs,
            history_messages=recent_messages,
            question=clean_question,
        )

        # 8. Invoke Gemini LLM
        try:
            llm = self._get_llm()
            llm_result = llm.invoke(prompt_messages)
            content = getattr(llm_result, "content", str(llm_result))
            if isinstance(content, list):
                text_blocks = [
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in content
                ]
                raw_answer = "".join(text_blocks)
            else:
                raw_answer = str(content)
            answer = sanitize_response(raw_answer)
            fallback_used = False
        except Exception:
            # Safe fallback if LLM invocation fails or API key missing
            answer = generate_fallback_response(business, clean_question)
            fallback_used = True

        # 9. Persist User Message and Assistant Response
        self._add_message(clean_bid, conv_id, "user", clean_question)
        self._add_message(clean_bid, conv_id, "assistant", answer)

        return RAGResponse(
            answer=answer,
            business_id=clean_bid,
            session_id=clean_sid,
            conversation_id=conv_id,
            retrieved_documents=retrieved_docs,
            fallback_triggered=fallback_used,
            metadata={"retrieved_doc_count": len(retrieved_docs)},
        )
