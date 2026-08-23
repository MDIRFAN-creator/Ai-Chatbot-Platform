
---

## `ARCHITECTURE.md`

```markdown
# SupportBot AI — V1 Architecture

## 1. Project Overview

SupportBot AI is a multi-tenant AI customer-support SaaS MVP.

A business provides structured information about its business, products, policies, and FAQs through a Streamlit dashboard.

The platform transforms this information into a business-specific RAG knowledge base.

The business can then:

1. Preview the chatbot.
2. Test the chatbot.
3. Generate an embeddable JavaScript widget.
4. Deploy the widget on its website.

The V1 is designed to demonstrate an end-to-end AI SaaS workflow using LangChain, RAG, embeddings, a vector store, Streamlit, and an embeddable chatbot widget.

---

# 2. V1 Technology Stack

## Frontend / Dashboard

- Streamlit
- Python

## AI / RAG

- LangChain
- Configurable LLM provider
- Configurable embedding provider
- Vector store: FAISS initially

## Database

- SQLite

## Validation

- Pydantic

## Widget

- HTML
- CSS
- JavaScript

## Version Control

- Git
- GitHub

## Deployment

- Streamlit Cloud initially

---

# 3. High-Level Architecture

```text
Business Owner
      |
      v
Streamlit Dashboard
      |
      v
Structured Forms
      |
      v
Pydantic Validation
      |
      v
SQLite
      |
      v
Knowledge Builder
      |
      v
LangChain Documents
      |
      v
Chunking
      |
      v
Embeddings
      |
      v
FAISS Vector Store
      |
      v
Business-Scoped Retriever
      |
      v
Prompt + Retrieved Context + Conversation History
      |
      v
LLM
      |
      v
Grounded Response

Customer-facing flow:

Customer
   |
   v
Embedded JavaScript Widget
   |
   v
Chatbot Backend
   |
   v
Identify business_id
   |
   v
Business-Scoped Retriever
   |
   v
RAG Pipeline
   |
   v
LLM
   |
   v
Response
4. Source of Truth

SQLite is the source of truth for structured business information.

SQLite stores:

Businesses
Assistant settings
Products
Policies
FAQs
Conversations
Messages
Knowledge document records

The vector store is NOT the source of truth.

The vector store exists for semantic retrieval.

5. Knowledge Architecture

The knowledge pipeline is:

Structured Business Data
        |
        v
Knowledge Builder
        |
        v
Normalized LangChain Documents
        |
        v
Chunking
        |
        v
Embeddings
        |
        v
Vector Store

Knowledge sources allowed in V1:

Business information
Products
Policies
FAQs

The RAG evaluation dataset must NEVER be inserted into the production knowledge base.

6. Document Strategy
Products

Normally:

One product = one LangChain Document.

FAQs

Normally:

One FAQ = one LangChain Document.

Policies

Policies can be represented as one or multiple documents depending on length.

Business Information

Business information can be represented as one or a small number of documents.

Documents must contain metadata.

Required metadata:

business_id
source_type
source_id

Optional metadata:

product_id
category
policy_type
faq_id
7. Multi-Tenancy

V1 is logically multi-tenant.

Every business has a unique business_id.

All business-owned records must be associated with business_id.

Examples:

Products
Policies
FAQs
Knowledge documents
Conversations

Retrieval must always be scoped to the current business_id.

A chatbot belonging to Business A must never retrieve Business B's knowledge.

8. RAG Query Flow
User Question
      |
      v
Identify business_id
      |
      v
Create query embedding
      |
      v
Business-scoped similarity search
      |
      v
Retrieve relevant documents
      |
      v
Construct prompt
      |
      +--> System instructions
      |
      +--> Business identity
      |
      +--> Retrieved context
      |
      +--> Recent conversation history
      |
      v
LLM
      |
      v
Grounded response
9. Grounding Rules

The chatbot must:

Answer using retrieved business information.
Avoid inventing business-specific facts.
Avoid inventing product prices.
Avoid inventing availability.
Avoid inventing policies.
Avoid inventing shipping information.
Avoid inventing refunds or returns.
State that information is unavailable when sufficient information cannot be retrieved.
Direct the customer to the business contact information when appropriate.

A relevance threshold or equivalent fallback mechanism should be used where practical.

10. Conversation Architecture

V1 supports short-term conversation history.

Conversation flow:

User message
     |
     v
Conversation history
     |
     v
Retriever
     |
     v
Retrieved context
     |
     v
LLM
     |
     v
Assistant response

Conversation history should be limited to recent relevant messages rather than indefinitely passing the entire conversation to the LLM.

11. Knowledge Updates

When a business edits:

Product information
Policy information
FAQ information
Business information

the system must provide a mechanism to regenerate or update the affected knowledge base.

The source database remains authoritative.

12. Dashboard Architecture

The Streamlit dashboard should contain:

Overview
Business Information
AI Assistant
Products
Policies
FAQs
Knowledge Base
Chatbot Preview
Embed
13. Embeddable Widget

The platform generates a JavaScript snippet similar to:

<script src="https://your-platform.example/widget.js" data-business-id="BUSINESS_ID"></script>

The widget must:

Identify the business.
Load the appropriate assistant configuration.
Display a floating chat button.
Display a chat window.
Send customer messages to the backend.
Include the correct business context in requests.
Display chatbot responses.

Private business knowledge must not be placed directly in client-side JavaScript.

14. V1 Non-Goals

Do NOT implement:

LangGraph
Multi-agent workflows
Tool calling
Live order management
Automated refunds
Automated cancellations
Automated returns
PDF uploads
DOCX uploads
Website scraping
CRM integrations
Helpdesk integrations
WhatsApp integration
Billing
Subscription management
Advanced analytics
Enterprise authentication
Voice interface

Do not add these features unless explicitly requested.

15. Engineering Principles
Prefer simple implementations suitable for an MVP.
Do not over-engineer.
Keep components modular.
Keep business data separate from evaluation data.
Never bypass business_id filtering.
Validate user input before persistence.
Keep secrets in environment variables.
Do not expose API keys to the browser.
Do not hardcode business-specific information into the RAG pipeline.
Keep provider-specific code configurable.
Write testable functions rather than putting all logic into Streamlit pages.
Avoid unnecessary dependencies.