# SupportBot AI — Product Requirements Document (PRD)

## 1. Product Overview

SupportBot AI is a multi-tenant AI customer-support SaaS MVP.

The platform allows businesses to create a customized AI customer-support chatbot by manually entering their business information, products, policies, and FAQs through a structured dashboard.

The platform then creates a business-specific RAG knowledge base and provides:

1. A chatbot preview.
2. A chatbot testing interface.
3. A generated JavaScript embed snippet.
4. An embeddable chatbot widget for the business website.

The V1 is intentionally limited in scope and focuses on demonstrating an end-to-end AI application using Streamlit, LangChain, RAG, embeddings, a vector store, SQLite, and an embeddable chatbot widget.

---

# 2. Problem

Small and medium-sized businesses often have repetitive customer-support questions about:

- Products
- Prices
- Availability
- Shipping
- Returns
- Refunds
- Payments
- General business information

Businesses may not have the resources to build a custom AI customer-support system.

SupportBot AI aims to allow a business to provide its information through a structured interface and quickly obtain an AI-powered support chatbot.

---

# 3. Target User

The primary user is a small or medium-sized business owner or operator.

Example:

A clothing brand called UrbanThreads signs up and enters:

- Business information
- Product information
- Shipping policy
- Return policy
- Refund policy
- FAQs

SupportBot AI then creates an AI assistant specialized for UrbanThreads.

---

# 4. V1 Product Flow

```text
Business Owner
      |
      v
Create Business
      |
      v
Enter Business Information
      |
      v
Add Products
      |
      v
Add Policies
      |
      v
Add FAQs
      |
      v
Build Knowledge Base
      |
      v
Test Chatbot
      |
      v
Preview Chatbot
      |
      v
Generate Embed Code
      |
      v
Embed Chatbot on Website

5. V1 Functional Requirements
5.1 Business Onboarding

The business must be able to provide:

Business name
Business description
Industry
Website
Contact email
Contact phone
Location

The information must be validated before being stored.

5.2 Product Management

The business must be able to create, edit, and delete products.

Each product should support:

Product name
Description
Category
Price
Currency
Sizes
Colors
Availability
Return eligibility
Product URL
5.3 Policy Management

The business must be able to create and edit policies.

V1 should support at minimum:

Shipping
Returns
Refunds

The architecture should allow additional policy types later.

5.4 FAQ Management

The business must be able to create, edit, and delete FAQs.

Each FAQ contains:

Question
Answer
5.5 AI Assistant Configuration

The business must be able to configure:

Assistant name
Tone
Welcome message

Example:

Assistant name:

UrbanThreads Assistant

Tone:

Friendly and professional

Welcome message:

"Hi! How can I help you with UrbanThreads today?"

5.6 Knowledge Base Generation

The platform must transform structured business information into a RAG knowledge base.

Knowledge sources include:

Business information
Products
Policies
FAQs

The knowledge pipeline should:

Retrieve structured data from SQLite.
Convert records into normalized text.
Create LangChain Documents.
Add metadata.
Split documents when necessary.
Generate embeddings.
Store vectors in the vector store.
5.7 Retrieval

The chatbot must retrieve information relevant to the customer's question.

Retrieval must be scoped to the current business.

The system must never retrieve information belonging to another business.

5.8 Chatbot

The chatbot must:

Answer customer questions.
Use retrieved business information.
Maintain short-term conversation context.
Avoid hallucinating business-specific information.
Admit when information is unavailable.
Provide business contact information when appropriate.
5.9 Unknown Questions

If the business knowledge base does not contain enough information to answer a question, the assistant should not guess.

Example:

"I don't have that information in my current knowledge base. Please contact UrbanThreads support for assistance."

5.10 Chatbot Preview

The business owner must be able to test the chatbot from the dashboard.

The preview should show:

User messages
Assistant messages
Conversation history
5.11 Embed Widget

The platform must generate a JavaScript snippet that the business can add to its website.

Example:

<script
    src="https://your-platform.example/widget.js"
    data-business-id="BUSINESS_ID">
</script>

The widget should:

Display a floating chat button.
Open a chat window.
Send messages to the chatbot backend.
Receive and display responses.
Identify the correct business.

Private business knowledge must not be exposed in client-side code.

5.12 Evaluation

The system must include an evaluation pipeline using a separate evaluation dataset.

Evaluation must test:

Retrieval relevance
Answer correctness
Groundedness
Abstention
Hallucination resistance
Semantic retrieval
Multi-turn conversation handling
Prompt injection resistance
Tenant isolation
6. V1 Technical Stack
Application
Python
Streamlit
AI
LangChain
LLM provider
Embedding provider
Database
SQLite
Vector Store
FAISS initially
Validation
Pydantic
Widget
HTML
CSS
JavaScript
Version Control
Git
GitHub
Deployment
Streamlit Cloud initially
7. Multi-Tenancy

Each business must have a unique business_id.

Business-owned information must be associated with business_id.

This includes:

Products
Policies
FAQs
Knowledge documents
Conversations

Retrieval must always be filtered/scoped using business_id.

8. Security Requirements

The application must:

Keep API keys in environment variables.
Never hardcode API keys.
Never expose API keys to the browser.
Validate user input.
Prevent cross-business retrieval.
Prevent evaluation data from entering the production knowledge base.
9. V1 Non-Goals

Do NOT implement:

PDF uploads
DOCX uploads
Website scraping
CRM integrations
Helpdesk integrations
WhatsApp integration
Voice interface
Automated refunds
Automated returns
Automated cancellations
Live order management
Billing
Subscription management
Advanced analytics
Multi-agent workflows
LangGraph
Tool calling
Enterprise authentication

These may be considered in future versions.

10. Success Criteria

The V1 is successful if:

A business can enter its information through structured forms.
The information is stored correctly.
The information can be converted into a RAG knowledge base.
The chatbot can answer business-specific questions.
The chatbot does not mix information between businesses.
The chatbot handles unknown questions safely.
The chatbot maintains short-term conversational context.
The chatbot can be previewed.
An embeddable widget can be generated.
The RAG system can be evaluated using the evaluation dataset.