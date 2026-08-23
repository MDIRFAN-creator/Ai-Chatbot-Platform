
---

## `RAG_DESIGN.md`

```markdown
# SupportBot AI — V1 RAG Design

## 1. Objective

Build a business-specific retrieval-augmented generation pipeline that allows each business's chatbot to answer customer-support questions using only the business's available knowledge.

The system must minimize hallucination and prevent cross-business retrieval.

---

# 2. Knowledge Sources

The production knowledge base can contain only:

1. Business information
2. Products
3. Policies
4. FAQs

The RAG evaluation dataset is NOT a knowledge source.

---

# 3. Knowledge Pipeline

```text
SQLite
   |
   v
Knowledge Builder
   |
   v
Normalized Text
   |
   v
LangChain Documents
   |
   v
Chunking
   |
   v
Embedding Model
   |
   v
Vector Store

4. LangChain Document Structure

Each document should contain:

Document(
    page_content="...",
    metadata={
        "business_id": "...",
        "source_type": "...",
        "source_id": "..."
    }
)

Additional metadata may be included when useful.

5. Source-Specific Document Strategy
Business

Convert relevant business information into normalized text.

Example:

Business Name: UrbanThreads

Description: ...

Industry: ...

Location: ...

Contact: ...

Product

Normally one product becomes one LangChain Document.

Example:

Product: Oversized Black Hoodie

Category: Hoodie

Price: ₹1,499

Sizes: S, M, L, XL

Colors: Black

Availability: In Stock

Returnable: Yes

Description: ...

Metadata:

{
    "business_id": "urbanthreads_001",
    "source_type": "product",
    "source_id": "product_id",
    "category": "hoodie"
}
Policy

Policy content should be normalized before embedding.

Metadata should include:

{
    "business_id": "...",
    "source_type": "policy",
    "source_id": "policy_id",
    "policy_type": "shipping"
}
FAQ

Normally one FAQ becomes one LangChain Document.

Example:

Question:
Is free shipping available?

Answer:
Yes. Orders above ₹1,499 qualify for free standard shipping.

Metadata:

{
    "business_id": "...",
    "source_type": "faq",
    "source_id": "faq_id"
}
6. Chunking

Do not blindly split every document into arbitrary chunks.

V1 strategy:

Products: generally one document per product.
FAQs: generally one document per FAQ.
Short business information: one document or small number of documents.
Policies: split only when necessary based on length.

If chunking is required, use a LangChain text splitter.

Chunking parameters should be configurable.

Do not hardcode values throughout the codebase.

7. Embeddings

Use a configurable embedding provider.

The embedding implementation must be isolated behind a reusable component.

The application should not hardcode the embedding provider throughout the RAG code.

8. Vector Store

V1 vector store:

FAISS initially.

The vector-store implementation should be isolated so that it can later be replaced with another vector database.

The vector store must preserve metadata required for business filtering.

9. Business-Scoped Retrieval

This is a mandatory security and correctness requirement.

Every retrieval operation must know the current business_id.

Conceptually:

retrieve(
    query=user_question,
    business_id=current_business_id
)

The retriever must only return documents belonging to current_business_id.

Never perform unrestricted global retrieval for a customer query.

10. Retrieval Flow
Customer Question
        |
        v
Current business_id
        |
        v
Query embedding
        |
        v
Business-scoped similarity search
        |
        v
Top-k relevant documents
        |
        v
Optional relevance threshold
        |
        v
Retrieved context
11. Prompt Construction

The final prompt should contain:

System instructions
Business identity
Assistant configuration
Retrieved knowledge
Recent conversation history
Current user question
Conceptually:

SYSTEM:
You are the customer-support assistant for {business_name}.

Follow these rules:
- Use the provided business context.
- Do not invent business-specific information.
- If the answer is not supported by the context, say that you do not have that information.
- Do not fabricate prices, policies, availability, shipping times, or refunds.
- Be concise and helpful.

BUSINESS:
{business information}

RETRIEVED CONTEXT:
{retrieved documents}

RECENT CONVERSATION:
{conversation history}

USER:
{question}
12. Unknown Questions

If retrieval does not produce sufficiently relevant information:

The system should not ask the LLM to guess.

Instead, use a fallback path.

Example:

I don't have that information in my current UrbanThreads knowledge base.
Please contact UrbanThreads support at support@urbanthreads.example.

The exact wording may be generated using configured business information, but the underlying behavior must remain grounded.

13. Conversation History

V1 supports short-term conversation context.

Recent conversation history may be passed to the LLM alongside retrieved context.

Conversation history must NOT replace retrieval.

For business-specific facts, retrieval remains the source of truth.

14. Retrieval vs Conversation Memory

Conversation history answers:

"What has the customer and assistant already discussed?"

RAG answers:

"What does the business knowledge base say?"

These are separate responsibilities.

15. Hallucination Prevention

The system must test questions such as:

Products that do not exist.
Unsupported prices.
Unsupported discounts.
Unsupported product colors.
Unsupported shipping promises.
Unsupported company information.
Out-of-domain questions.

The chatbot should safely state that it does not have the requested information when the knowledge base does not support an answer.

16. Tenant Isolation

The RAG layer must enforce:

business_id = current_business_id

at retrieval time.

A document from:

business_id = business_A

must never be returned for:

business_id = business_B
17. Knowledge Updates

When source information changes:

Database update
      |
      v
Knowledge document regeneration
      |
      v
Re-embedding
      |
      v
Vector store update

V1 may rebuild the business-specific vector index rather than implementing highly optimized incremental updates.

Prefer correctness and simplicity over premature optimization.

18. RAG Debugging

The system should make it possible during development to inspect:

User query
business_id
Retrieved documents
Metadata
Similarity/relevance information where available
Final prompt context
Generated response

Do not expose internal debugging information to normal customers.

19. Evaluation Dataset Separation

The evaluation dataset is strictly separate from production knowledge.

Do NOT:

Embed evaluation questions.
Embed expected answers.
Add evaluation records to knowledge_documents.
Add evaluation records to the vector store.

Evaluation data is used only by the evaluation runner.

20. V1 RAG Goal

The goal is not to build the most advanced RAG architecture.

The goal is to build a:

Correct
Grounded
Business-scoped
Testable
Understandable
Modular
