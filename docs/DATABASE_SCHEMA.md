
---

## `DATABASE_SCHEMA.md`

```markdown
# SupportBot AI — V1 Database Schema

## Database

SQLite

SQLite is the source of truth for structured application data.

The vector store is used only for semantic retrieval.

---

# 1. businesses

Stores the business/tenant profile.

Fields:

- business_id: TEXT PRIMARY KEY
- name: TEXT NOT NULL
- description: TEXT
- industry: TEXT
- website: TEXT
- contact_email: TEXT
- contact_phone: TEXT
- location: TEXT
- created_at: DATETIME
- updated_at: DATETIME

Relationship:

One business has many products, policies, FAQs, conversations, and knowledge documents.

---

# 2. assistant_settings

Stores AI assistant configuration.

Fields:

- assistant_id: TEXT PRIMARY KEY
- business_id: TEXT NOT NULL
- assistant_name: TEXT NOT NULL
- tone: TEXT
- welcome_message: TEXT
- created_at: DATETIME
- updated_at: DATETIME

Relationship:

One business has one assistant configuration for V1.

business_id must reference businesses.business_id.

---

# 3. products

Stores product information.

Fields:

- product_id: TEXT PRIMARY KEY
- business_id: TEXT NOT NULL
- name: TEXT NOT NULL
- description: TEXT
- price: REAL
- currency: TEXT
- category: TEXT
- sizes: TEXT
- colors: TEXT
- availability: TEXT
- returnable: BOOLEAN
- product_url: TEXT
- created_at: DATETIME
- updated_at: DATETIME

business_id must reference businesses.business_id.

A product belongs to exactly one business.

For V1, sizes and colors may be stored as JSON-encoded text.

Example:

["S", "M", "L", "XL"]

---

# 4. policies

Stores business policies.

Fields:

- policy_id: TEXT PRIMARY KEY
- business_id: TEXT NOT NULL
- policy_type: TEXT NOT NULL
- content: TEXT NOT NULL
- created_at: DATETIME
- updated_at: DATETIME

Examples of policy_type:

- shipping
- returns
- refunds
- payment
- sizing

The V1 UI must at minimum support:

- shipping
- returns
- refunds

business_id must reference businesses.business_id.

---

# 5. faqs

Stores frequently asked questions.

Fields:

- faq_id: TEXT PRIMARY KEY
- business_id: TEXT NOT NULL
- question: TEXT NOT NULL
- answer: TEXT NOT NULL
- created_at: DATETIME
- updated_at: DATETIME

business_id must reference businesses.business_id.

---

# 6. knowledge_documents

Stores the normalized knowledge representation used to construct the RAG index.

Fields:

- knowledge_id: TEXT PRIMARY KEY
- business_id: TEXT NOT NULL
- source_type: TEXT NOT NULL
- source_id: TEXT NOT NULL
- content: TEXT NOT NULL
- metadata: TEXT
- created_at: DATETIME
- updated_at: DATETIME

source_type examples:

- business
- product
- policy
- faq

metadata should contain JSON-encoded metadata.

Required metadata:

- business_id
- source_type
- source_id

Optional metadata:

- product_id
- category
- policy_type
- faq_id

business_id must reference businesses.business_id.

---

# 7. conversations

Stores customer chat sessions.

Fields:

- conversation_id: TEXT PRIMARY KEY
- business_id: TEXT NOT NULL
- session_id: TEXT NOT NULL
- created_at: DATETIME
- updated_at: DATETIME

business_id must reference businesses.business_id.

---

# 8. messages

Stores individual conversation messages.

Fields:

- message_id: TEXT PRIMARY KEY
- conversation_id: TEXT NOT NULL
- role: TEXT NOT NULL
- content: TEXT NOT NULL
- timestamp: DATETIME

Allowed roles:

- user
- assistant

conversation_id must reference conversations.conversation_id.

---

# 9. Relationships

```text
businesses
    |
    +---- assistant_settings
    |
    +---- products
    |
    +---- policies
    |
    +---- faqs
    |
    +---- knowledge_documents
    |
    +---- conversations
               |
               +---- messages

10. Multi-Tenant Requirement

Every business-owned entity must be associated with business_id.

Queries must always respect business_id.

Example:

Correct:

SELECT *
FROM products
WHERE business_id = ?;

Incorrect:

SELECT *
FROM products;

The application must never return another business's records.

11. Source of Truth Rule

SQLite is authoritative.

If a product changes:

Update SQLite.
Regenerate/update the corresponding knowledge document.
Update the vector store.

Do not manually modify vector-store records as the primary data-management mechanism.

12. Evaluation Data

The RAG evaluation dataset must NOT be stored in the production knowledge_documents table.

Evaluation data belongs in the evaluation subsystem.

It must never be embedded into the production vector store.