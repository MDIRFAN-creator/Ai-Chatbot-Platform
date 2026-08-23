# SupportBot AI — AI Customer Support Automation Platform

SupportBot AI is a multi-tenant AI customer-support SaaS MVP. It enables businesses to configure a customized AI customer-support assistant by manually providing structured business data, product catalogs, policies, and FAQs through a web dashboard. The platform generates a business-specific RAG knowledge base, provides an interactive preview and testing interface, and generates an embeddable JavaScript widget for business websites.

> **Current Status: Early Development (Phase 1 — Project Initialization & Development Foundation)**
> This project is being developed strictly phase-by-phase. Core application features (database CRUD, RAG pipeline, dashboard pages, and evaluation runner) are not yet implemented and will be built in subsequent phases.

---

## V1 Technology Stack

* **UI & Dashboard**: Streamlit
* **AI Orchestration**: LangChain
* **LLM Provider**: Google Gemini API (Configurable)
* **Embedding Model**: Local Hugging Face / Sentence Transformers (`sentence-transformers/all-MiniLM-L6-v2`)
* **Vector Store**: FAISS (CPU)
* **Database**: SQLite
* **Schema Validation**: Pydantic
* **Web Widget**: HTML, CSS, JavaScript
* **Testing**: Pytest

---

## Getting Started

### 1. Prerequisites
* Python 3.10+
* Git

### 2. Virtual Environment Setup

**Windows PowerShell:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Update `.env` with your Google Gemini API key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

---

## Project Structure Overview

```text
AI Chatbot Platform/
├── docs/             # Architectural specifications and design docs
├── app/              # Streamlit dashboard & UI components
├── core/             # Core infrastructure: configuration, database engine, models
├── data/             # Evaluation datasets and seed data
├── knowledge/        # Knowledge normalization and document builders
├── rag/              # Embeddings, vector store, retriever, prompts, chains
├── services/         # Business logic layer
├── evaluation/       # Evaluation runner, metrics, and benchmarking
├── widget/           # Embeddable JavaScript widget
└── tests/            # Automated test suite
```
