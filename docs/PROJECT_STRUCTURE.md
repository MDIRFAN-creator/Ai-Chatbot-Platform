"""# PROJECT_STRUCTURE.md

# 1. Project Structure

The V1 project is an AI Customer Support Automation Platform built with LangChain and Streamlit.

The structure below is the source of truth for where application code, business data, RAG components, evaluation components, tests, and documentation belong.

```text
ai-customer-support-platform/
│
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── RAG_DESIGN.md
│   ├── EVALUATION_PLAN.md
│   └── PROJECT_STRUCTURE.md
│
├── app/
│   ├── main.py
│   │
│   ├── pages/
│   │   ├── dashboard.py
│   │   ├── business_setup.py
│   │   ├── products.py
│   │   ├── policies.py
│   │   ├── faqs.py
│   │   ├── assistant_settings.py
│   │   ├── knowledge_base.py
│   │   ├── chatbot.py
│   │   └── evaluation.py
│   │
│   └── components/
│       ├── forms.py
│       ├── chat_ui.py
│       ├── product_cards.py
│       └── common.py
│
├── core/
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   └── security.py
│
├── data/
│   ├── evaluation/
│   │   └── urbanthreads_evaluation.json
│   │
│   └── seed/
│       └── urbanthreads/
│           └── README.md
│
├── knowledge/
│   ├── document_builder.py
│   ├── document_loader.py
│   ├── metadata.py
│   └── knowledge_manager.py
│
├── rag/
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── retriever.py
│   ├── prompts.py
│   ├── chain.py
│   ├── memory.py
│   └── guardrails.py
│
├── services/
│   ├── business_service.py
│   ├── product_service.py
│   ├── policy_service.py
│   ├── faq_service.py
│   ├── assistant_service.py
│   ├── knowledge_service.py
│   └── conversation_service.py
│
├── evaluation/
│   ├── runner.py
│   ├── metrics.py
│   ├── evaluators.py
│   ├── test_cases.py
│   └── report.py
│
├── widget/
│   ├── README.md
│   └── embed.js
│
└── tests/
    ├── test_database.py
    ├── test_knowledge.py
    ├── test_retrieval.py
    ├── test_rag.py
    ├── test_multi_tenant.py
    └── test_evaluation.py
2. Directory Responsibilities
2.1 docs/

Contains the project specification and engineering documentation.

These documents are provided to Cursor as project context and should be treated as the project's source of truth.

PRD.md — product requirements and V1 scope.
ARCHITECTURE.md — system architecture and application flow.
DATABASE_SCHEMA.md — database entities, relationships, and tenant requirements.
RAG_DESIGN.md — RAG pipeline, retrieval, grounding, chunking, embeddings, and knowledge updates.
EVALUATION_PLAN.md — evaluation methodology and metrics.
PROJECT_STRUCTURE.md — repository structure and responsibilities.

Do not place application logic in the docs/ directory.

2.2 app/

Contains the Streamlit user interface.

The V1 dashboard allows a business to:

Create/configure its business information.
Add products.
Add policies.
Add FAQs.
Configure its AI assistant.
Generate/update its knowledge base.
Preview the chatbot.
Run/view evaluation results.

app/ should contain UI and presentation logic. Core RAG logic should remain outside this directory.

2.3 core/

Contains application-wide infrastructure.

Responsibilities include:

Configuration.
Database connection.
Shared database models.
Security utilities.
Environment configuration.

Business-specific operations should be implemented in services/, not directly inside the UI.

2.4 data/

Contains local development and evaluation data.

data/evaluation/

Contains datasets used only by the evaluation system.

The UrbanThreads evaluation dataset is:

data/evaluation/urbanthreads_evaluation.json

This dataset must NOT be inserted into the production RAG knowledge base.

It is used to test the chatbot.

data/seed/

Contains optional development/seed information used to populate the V1 database during development.

The production application must treat the structured dashboard/database as the source of truth.

2.5 knowledge/

Responsible for transforming structured business information into LangChain documents and managing knowledge-base generation.

Responsibilities include:

Building documents from business information.
Building product documents.
Building policy documents.
Building FAQ documents.
Attaching metadata.
Creating/updating knowledge documents.
Coordinating knowledge-base regeneration.

The knowledge layer should consume structured data from the database rather than treating the evaluation dataset as knowledge.

2.6 rag/

Contains the Retrieval-Augmented Generation implementation.

Responsibilities include:

Embedding model configuration.
Vector store configuration.
Retriever creation.
Business-scoped retrieval.
Prompt construction.
LangChain chain construction.
Conversation memory.
Grounding and unknown-question guardrails.

The RAG layer must always respect the current business/tenant ID.

2.7 services/

Contains application/business logic between the UI and infrastructure.

Examples:

business_service.py — business information operations.
product_service.py — product CRUD operations.
policy_service.py — policy CRUD operations.
faq_service.py — FAQ CRUD operations.
assistant_service.py — assistant configuration.
knowledge_service.py — knowledge-base generation/update operations.
conversation_service.py — conversation and message handling.

The service layer keeps Streamlit pages from becoming tightly coupled to the database and RAG implementation.

2.8 evaluation/

Contains the automated evaluation pipeline.

Responsibilities include:

Loading the evaluation dataset.
Running test cases against the chatbot.
Capturing chatbot responses.
Capturing retrieved documents/context where available.
Evaluating retrieval relevance.
Evaluating answer correctness.
Evaluating groundedness.
Evaluating abstention/unknown-question behavior.
Evaluating policy reasoning.
Evaluating multi-turn behavior.
Evaluating out-of-domain behavior.
Evaluating prompt-injection resistance.
Evaluating tenant isolation.
Producing evaluation reports.

The evaluation pipeline must remain separate from the production knowledge pipeline.

2.9 widget/

Contains the V1 embeddable chatbot widget.

The widget is responsible for providing a small client-side integration that a business can place on its website.

The V1 implementation should remain simple.

The widget communicates with the chatbot backend and identifies the business/assistant it belongs to.

2.10 tests/

Contains automated tests for important application behavior.

Tests should cover:

Database behavior.
Knowledge-document generation.
Retrieval.
RAG behavior.
Tenant isolation.
Evaluation pipeline.
3. Data Separation

The project has two fundamentally different data paths.

3.1 Production Business Data

Business information is entered through the Streamlit dashboard.

Business
   │
   ├── Business Information
   ├── Products
   ├── Policies
   └── FAQs
          │
          ▼
       Database
          │
          ▼
   Knowledge Generation
          │
          ▼
   LangChain Documents
          │
          ▼
     Vector Store
          │
          ▼
        RAG

This is the production chatbot knowledge path.

3.2 Evaluation Data

Evaluation data follows a separate path.

urbanthreads_evaluation.json
          │
          ▼
   Evaluation Runner
          │
          ▼
      Chatbot/RAG
          │
          ▼
   Actual Response
          │
          ▼
     Evaluators
          │
          ▼
    Evaluation Report

The evaluation dataset must never be embedded into the production vector store.

4. Business Data Flow

For V1, a business manually enters its information through structured forms.

Streamlit Dashboard
        │
        ├── Business Information
        ├── Products
        ├── Policies
        └── FAQs
                │
                ▼
             Database
                │
                ▼
       Knowledge Base Builder
                │
                ▼
       LangChain Documents
                │
                ▼
          Embeddings
                │
                ▼
          Vector Store
                │
                ▼
             Retriever
                │
                ▼
              LLM
                │
                ▼
           AI Assistant

The V1 project does not require businesses to upload arbitrary documents as the primary onboarding mechanism.

5. Evaluation Data Flow

The evaluation dataset is developer-controlled test data.

data/evaluation/
urbanthreads_evaluation.json
              │
              ▼
       evaluation/runner.py
              │
              ▼
      Test each evaluation case
              │
              ▼
       Chatbot/RAG Pipeline
              │
              ├── Retrieved Context
              └── Final Answer
                      │
                      ▼
              evaluation/evaluators.py
                      │
          ┌───────────┼────────────┐
          ▼           ▼            ▼
      Retrieval    Correctness   Grounding
          │           │            │
          └───────────┼────────────┘
                      ▼
             evaluation/report.py
6. Multi-Tenant Structure

Every business/customer is treated as a separate tenant.

At minimum, tenant-aware data must include:

business_id

Business-scoped information includes:

Products.
Policies.
FAQs.
Assistant settings.
Knowledge documents.
Conversations.
Messages.
Vector-store metadata.

The application must never retrieve one business's knowledge while serving another business.

Example:

business_id = urbanthreads_001

must retrieve only UrbanThreads knowledge.

7. V1 Architectural Boundary

The following boundaries should be maintained:

UI
 ↓
Services
 ↓
Database / Knowledge / RAG
 ↓
LLM

The evaluation system is separate:

Evaluation Dataset
 ↓
Evaluation Runner
 ↓
Production Chatbot Interface
 ↓
Evaluation Metrics

The evaluation dataset should not bypass the chatbot and directly evaluate raw documents unless a specific retrieval-level test requires it.