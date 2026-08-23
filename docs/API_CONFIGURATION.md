# API_CONFIGURATION.md

## 1. Purpose

This document defines the external API providers, local AI components, credentials, environment variables, and configuration rules for the V1 AI Customer Support Automation Platform.

The V1 follows a free/free-tier-first approach. Provider-specific implementation must remain configurable.

## 2. V1 Technology Configuration

| Component | V1 Choice | API Required | Cost Strategy |
|---|---|---|---|
| UI / Dashboard | Streamlit | No | Free |
| AI Framework | LangChain | No | Open source |
| LLM | Gemini API | Yes | Free tier for development |
| Embeddings | Local Hugging Face / Sentence Transformers | No | Free/local |
| Vector Store | FAISS | No | Local/free |
| Database | SQLite | No | Local/free |
| Widget | HTML/CSS/JavaScript | No | Free |
| Deployment | Streamlit Cloud initially | No separate API | Free tier where available |
| Version Control | Git/GitHub | No API key required for basic Git operations | Free |

## 3. LLM Provider

V1 uses Google Gemini through the Gemini API.

The provider must be configurable and must not be hard-coded throughout the application.

```env
LLM_PROVIDER=gemini
LLM_MODEL=<selected Gemini model>
```

Create the Gemini API key through Google AI Studio.

Official documentation: https://ai.google.dev/gemini-api/docs/get-started

Python SDK:

```bash
pip install -U google-genai
```

Required secret:

```env
GEMINI_API_KEY=
```

Never hard-code or commit the key.

## 4. Embedding Provider

V1 uses a local Hugging Face/Sentence Transformers embedding model.

No embedding API key is required.

Recommended initial model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Configuration:

```env
EMBEDDING_PROVIDER=huggingface_local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

The model is downloaded once and then used locally.

## 5. Installing Local Hugging Face Embeddings

Use Python 3.10+.

From the project root, create a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

Install Sentence Transformers:

```bash
pip install -U sentence-transformers
```

Install the LangChain integration:

```bash
pip install -U langchain-huggingface
```

Example:

```python
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
```

The application should initialize the embedding model through the configuration layer rather than constructing it throughout the codebase.

## 6. Embedding Flow

Production knowledge pipeline:

```text
Business Structured Data
        |
        v
LangChain Documents
        |
        v
Text Chunks
        |
        v
Local Hugging Face Embedding Model
        |
        v
Vectors
        |
        v
FAISS
```

Query pipeline:

```text
User Question
        |
        v
Local Hugging Face Embedding Model
        |
        v
Query Vector
        |
        v
FAISS Similarity Search
        |
        v
Relevant Documents
```

Use the same embedding model for indexing and querying.

## 7. Vector Store

V1 uses FAISS. It requires no API key.

Recommended persistence:

```text
vectorstore/
└── <business_id>/
    └── faiss_index/
```

Example:

```text
vectorstore/
└── urbanthreads_001/
    └── faiss_index/
```

The vector store must be business-scoped.

## 8. Database

V1 uses SQLite.

Recommended path:

```text
data/supportbot.db
```

SQLite stores:

- businesses
- assistant_settings
- products
- policies
- faqs
- knowledge_documents
- conversations
- messages

SQLite is the source of truth for structured business information.

FAISS is the retrieval index, not the authoritative business database.

## 9. Evaluation Dataset

The evaluation dataset remains separate:

```text
data/
└── evaluation/
    └── urbanthreads_evaluation.json
```

It must never be embedded into the production FAISS index.

Evaluation flow:

```text
urbanthreads_evaluation.json
        |
        v
Evaluation Runner
        |
        v
Chatbot
        |
        v
RAG Pipeline
        |
        v
Actual Response
        |
        v
Evaluation Metrics
```

## 10. Environment Variables

Example `.env`:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=

LLM_MODEL=

EMBEDDING_PROVIDER=huggingface_local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

DATABASE_URL=sqlite:///data/supportbot.db

RETRIEVAL_TOP_K=5

APP_ENV=development
DEBUG=true
```

## 11. `.env.example`

Commit `.env.example`, not `.env`.

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=

LLM_MODEL=

EMBEDDING_PROVIDER=huggingface_local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

DATABASE_URL=sqlite:///data/supportbot.db

RETRIEVAL_TOP_K=5

APP_ENV=development
DEBUG=true
```

## 12. Git Security

`.gitignore` must include:

```text
.env
.venv/
__pycache__/
*.pyc
data/*.db
vectorstore/
```

Never commit API keys, local databases, virtual environments, or generated FAISS indexes.

## 13. Provider Abstraction

Provider-specific code should be isolated.

Recommended locations:

```text
core/
└── config.py

rag/
├── llm.py
├── embeddings.py
└── vector_store.py
```

The rest of the RAG pipeline should depend on these abstractions rather than directly constructing providers throughout the application.

## 14. V1 Provider Decision

```text
LLM
    Gemini API

Embeddings
    Local Hugging Face / Sentence Transformers

Vector Store
    FAISS

Database
    SQLite
```

## 15. Future Provider Options

Possible future providers include:

```text
LLM:
    OpenAI
    Gemini
    Local/Ollama

Embeddings:
    OpenAI
    Hugging Face
    Other local embedding models

Vector Store:
    FAISS
    Chroma
    Pinecone
    Other production vector databases

Database:
    SQLite
    PostgreSQL
```

These are future options and are not required for V1.

## 16. Engineering Rules

1. Never hard-code secrets.
2. Never expose API keys to the frontend/widget.
3. Keep provider configuration in the configuration layer.
4. Use the same embedding model for indexing and retrieval.
5. Keep evaluation data separate from production knowledge.
6. Keep SQLite as the source of truth for structured business data.
7. Keep FAISS as the retrieval index.
8. Preserve `business_id` throughout the knowledge and retrieval pipeline.
9. Do not introduce external services unless required by the V1 PRD.
10. Prefer local/free components where they satisfy V1 requirements.

## 17. External API Summary

The only required external API for initial development is:

```text
Google Gemini API
    |
    └── GEMINI_API_KEY
```

The embedding model, database, vector store, LangChain orchestration, Streamlit UI, and evaluation pipeline can run locally without separate paid APIs.
