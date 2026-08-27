"""SQLite database persistence layer and CRUD foundation for SupportBot AI.

This module manages database connections, table creation, schema initialization,
and multi-tenant validated CRUD operations for all core entities.
"""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Generator, List, Optional, Union
import uuid

from core.config import config, get_config
from core.models import (
    AssistantSettings,
    AssistantSettingsCreate,
    AssistantSettingsUpdate,
    Business,
    BusinessCreate,
    BusinessUpdate,
    Conversation,
    ConversationCreate,
    FAQ,
    FAQCreate,
    FAQUpdate,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    Message,
    MessageCreate,
    Policy,
    PolicyCreate,
    PolicyUpdate,
    Product,
    ProductCreate,
    ProductUpdate,
    get_utc_now_iso,
)

# SQL DDL for table and index creation
SCHEMA_DDL = """
-- 1. Businesses
CREATE TABLE IF NOT EXISTS businesses (
    business_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    industry TEXT,
    website TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    location TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. Assistant Settings (One-to-One with Business)
CREATE TABLE IF NOT EXISTS assistant_settings (
    assistant_id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL UNIQUE,
    assistant_name TEXT NOT NULL,
    tone TEXT,
    welcome_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_assistant_settings_business_id ON assistant_settings(business_id);

-- 3. Products
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price REAL,
    currency TEXT DEFAULT 'USD',
    category TEXT,
    sizes TEXT DEFAULT '[]',
    colors TEXT DEFAULT '[]',
    availability TEXT DEFAULT 'in_stock',
    returnable INTEGER DEFAULT 1,
    product_url TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_products_business_id ON products(business_id);

-- 4. Policies
CREATE TABLE IF NOT EXISTS policies (
    policy_id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    policy_type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_policies_business_id ON policies(business_id);
CREATE INDEX IF NOT EXISTS idx_policies_business_type ON policies(business_id, policy_type);

-- 5. FAQs
CREATE TABLE IF NOT EXISTS faqs (
    faq_id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_faqs_business_id ON faqs(business_id);

-- 6. Knowledge Documents
CREATE TABLE IF NOT EXISTS knowledge_documents (
    knowledge_id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_business_id ON knowledge_documents(business_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_source ON knowledge_documents(business_id, source_type, source_id);

-- 7. Conversations
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES businesses(business_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_conversations_business_id ON conversations(business_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(business_id, session_id);

-- 8. Messages
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
"""


def _generate_id(prefix: str = "") -> str:
    """Generate a unique random identifier."""
    unique_id = uuid.uuid4().hex
    return f"{prefix}_{unique_id}" if prefix else unique_id


def resolve_db_path(db_path: Optional[Union[str, Path]] = None) -> Union[str, Path]:
    """Resolve the target SQLite database path from parameter or application config."""
    if db_path is not None:
        if str(db_path) == ":memory:":
            return ":memory:"
        return db_path
    cfg = get_config()
    raw_path = cfg.database_path
    if str(raw_path) == ":memory:":
        return ":memory:"
    return raw_path


def create_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Create and configure a raw SQLite connection with foreign keys and row factory enabled."""
    target_path = resolve_db_path(db_path)
    is_memory = str(target_path) == ":memory:" or (
        isinstance(target_path, str) and "mode=memory" in target_path
    )

    if not is_memory:
        path_obj = Path(target_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path_obj))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
    else:
        conn = sqlite3.connect(
            target_path if isinstance(target_path, str) else ":memory:",
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")

    return conn


@contextmanager
def get_connection(
    db_path: Optional[Union[str, Path]] = None
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with automatic commit and rollback."""
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """Initialize the SQLite database schema and create all 8 tables if they do not exist."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_DDL)


class DatabaseManager:
    """Multi-tenant database repository and CRUD manager."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = db_path

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        with get_connection(self.db_path) as conn:
            yield conn

    def initialize(self) -> None:
        """Initialize the database schema."""
        init_db(self.db_path)

    # =================================================================
    # 1. BUSINESS CRUD
    # =================================================================

    def create_business(self, data: Union[BusinessCreate, Dict[str, Any]]) -> Business:
        """Create a new business record."""
        create_model = BusinessCreate.model_validate(data) if isinstance(data, dict) else data
        now = get_utc_now_iso()
        business_id = create_model.business_id or _generate_id("biz")

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO businesses (
                    business_id, name, description, industry, website,
                    contact_email, contact_phone, location, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    business_id,
                    create_model.name,
                    create_model.description,
                    create_model.industry,
                    create_model.website,
                    create_model.contact_email,
                    create_model.contact_phone,
                    create_model.location,
                    now,
                    now,
                ),
            )

        return self.get_business(business_id)  # type: ignore[return-value]

    def get_business(self, business_id: str) -> Optional[Business]:
        """Retrieve a business by ID."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM businesses WHERE business_id = ?",
                (business_id,),
            ).fetchone()
            if not row:
                return None
            return Business.model_validate(dict(row))

    def update_business(
        self, business_id: str, data: Union[BusinessUpdate, Dict[str, Any]]
    ) -> Optional[Business]:
        """Update an existing business record."""
        update_model = BusinessUpdate.model_validate(data) if isinstance(data, dict) else data
        update_dict = update_model.model_dump(exclude_unset=True)
        if not update_dict:
            return self.get_business(business_id)

        update_dict["updated_at"] = get_utc_now_iso()
        set_clauses = [f"{k} = ?" for k in update_dict.keys()]
        values = list(update_dict.values()) + [business_id]

        with self._conn() as conn:
            cursor = conn.execute(
                f"UPDATE businesses SET {', '.join(set_clauses)} WHERE business_id = ?",
                values,
            )
            if cursor.rowcount == 0:
                return None

        return self.get_business(business_id)

    def delete_business(self, business_id: str) -> bool:
        """Delete a business by ID (cascades to child tables)."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM businesses WHERE business_id = ?",
                (business_id,),
            )
            return cursor.rowcount > 0

    def list_businesses(self) -> List[Business]:
        """List all businesses in the platform."""
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM businesses ORDER BY created_at ASC").fetchall()
            return [Business.model_validate(dict(row)) for row in rows]

    # =================================================================
    # 2. ASSISTANT SETTINGS CRUD (1:1 per Business)
    # =================================================================

    def get_assistant_settings(self, business_id: str) -> Optional[AssistantSettings]:
        """Get assistant configuration for a specific business."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM assistant_settings WHERE business_id = ?",
                (business_id,),
            ).fetchone()
            if not row:
                return None
            return AssistantSettings.model_validate(dict(row))

    def create_or_update_assistant_settings(
        self,
        data: Union[AssistantSettingsCreate, AssistantSettingsUpdate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> AssistantSettings:
        """Create or update the assistant settings for a business (upsert pattern)."""
        target_business_id = (
            business_id
            or (data.business_id if isinstance(data, AssistantSettingsCreate) else None)
            or (data.get("business_id") if isinstance(data, dict) else None)
        )
        if not target_business_id:
            raise ValueError("business_id is required to create or update assistant settings")

        existing = self.get_assistant_settings(target_business_id)
        now = get_utc_now_iso()

        if existing:
            update_data = (
                AssistantSettingsUpdate.model_validate(data)
                if not isinstance(data, AssistantSettingsUpdate)
                else data
            )
            update_dict = update_data.model_dump(exclude_unset=True)
            update_dict["updated_at"] = now
            set_clauses = [f"{k} = ?" for k in update_dict.keys()]
            values = list(update_dict.values()) + [existing.assistant_id]

            with self._conn() as conn:
                conn.execute(
                    f"UPDATE assistant_settings SET {', '.join(set_clauses)} WHERE assistant_id = ?",
                    values,
                )
            return self.get_assistant_settings(target_business_id)  # type: ignore[return-value]

        # Insert new
        create_data = (
            AssistantSettingsCreate.model_validate(data)
            if not isinstance(data, AssistantSettingsCreate)
            else data
        )
        assistant_id = create_data.assistant_id or _generate_id("asst")

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO assistant_settings (
                    assistant_id, business_id, assistant_name, tone,
                    welcome_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assistant_id,
                    target_business_id,
                    create_data.assistant_name,
                    create_data.tone,
                    create_data.welcome_message,
                    now,
                    now,
                ),
            )

        return self.get_assistant_settings(target_business_id)  # type: ignore[return-value]

    def delete_assistant_settings(self, business_id: str) -> bool:
        """Delete assistant settings for a business."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM assistant_settings WHERE business_id = ?",
                (business_id,),
            )
            return cursor.rowcount > 0

    # =================================================================
    # 3. PRODUCT CRUD
    # =================================================================

    def _row_to_product(self, row: sqlite3.Row) -> Product:
        """Convert a database row into a Product model with JSON deserialization."""
        d = dict(row)
        d["sizes"] = json.loads(d.get("sizes") or "[]")
        d["colors"] = json.loads(d.get("colors") or "[]")
        d["returnable"] = bool(d.get("returnable", 1))
        return Product.model_validate(d)

    def create_product(self, data: Union[ProductCreate, Dict[str, Any]]) -> Product:
        """Create a new product for a business."""
        create_model = ProductCreate.model_validate(data) if isinstance(data, dict) else data
        now = get_utc_now_iso()
        product_id = create_model.product_id or _generate_id("prod")
        sizes_json = json.dumps(create_model.sizes or [])
        colors_json = json.dumps(create_model.colors or [])
        returnable_int = 1 if create_model.returnable else 0

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO products (
                    product_id, business_id, name, description, price,
                    currency, category, sizes, colors, availability,
                    returnable, product_url, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    create_model.business_id,
                    create_model.name,
                    create_model.description,
                    create_model.price,
                    create_model.currency,
                    create_model.category,
                    sizes_json,
                    colors_json,
                    create_model.availability,
                    returnable_int,
                    create_model.product_url,
                    now,
                    now,
                ),
            )

        return self.get_product(product_id, create_model.business_id)  # type: ignore[return-value]

    def get_product(
        self, product_id: str, business_id: Optional[str] = None
    ) -> Optional[Product]:
        """Retrieve a single product by ID, optionally verifying business ownership."""
        query = "SELECT * FROM products WHERE product_id = ?"
        params: List[Any] = [product_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            return self._row_to_product(row)

    def update_product(
        self,
        product_id: str,
        data: Union[ProductUpdate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> Optional[Product]:
        """Update a product with tenant isolation enforcement."""
        update_model = ProductUpdate.model_validate(data) if isinstance(data, dict) else data
        raw_dict = update_model.model_dump(exclude_unset=True)
        if not raw_dict:
            return self.get_product(product_id, business_id)

        update_dict: Dict[str, Any] = {}
        for k, v in raw_dict.items():
            if k == "sizes":
                update_dict["sizes"] = json.dumps(v or [])
            elif k == "colors":
                update_dict["colors"] = json.dumps(v or [])
            elif k == "returnable":
                update_dict["returnable"] = 1 if v else 0
            else:
                update_dict[k] = v

        update_dict["updated_at"] = get_utc_now_iso()
        set_clauses = [f"{k} = ?" for k in update_dict.keys()]
        values = list(update_dict.values()) + [product_id]

        query = f"UPDATE products SET {', '.join(set_clauses)} WHERE product_id = ?"
        if business_id is not None:
            query += " AND business_id = ?"
            values.append(business_id)

        with self._conn() as conn:
            cursor = conn.execute(query, values)
            if cursor.rowcount == 0:
                return None

        return self.get_product(product_id, business_id)

    def delete_product(self, product_id: str, business_id: Optional[str] = None) -> bool:
        """Delete a product, optionally enforcing tenant ownership."""
        query = "DELETE FROM products WHERE product_id = ?"
        params: List[Any] = [product_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def get_products_by_business(self, business_id: str) -> List[Product]:
        """Retrieve all products strictly belonging to a specific business."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM products WHERE business_id = ? ORDER BY created_at ASC",
                (business_id,),
            ).fetchall()
            return [self._row_to_product(row) for row in rows]

    # =================================================================
    # 4. POLICY CRUD
    # =================================================================

    def create_policy(self, data: Union[PolicyCreate, Dict[str, Any]]) -> Policy:
        """Create a new policy record."""
        create_model = PolicyCreate.model_validate(data) if isinstance(data, dict) else data
        now = get_utc_now_iso()
        policy_id = create_model.policy_id or _generate_id("pol")

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO policies (
                    policy_id, business_id, policy_type, content, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    policy_id,
                    create_model.business_id,
                    create_model.policy_type,
                    create_model.content,
                    now,
                    now,
                ),
            )

        return self.get_policy(policy_id, create_model.business_id)  # type: ignore[return-value]

    def get_policy(
        self, policy_id: str, business_id: Optional[str] = None
    ) -> Optional[Policy]:
        """Retrieve a policy by ID with optional business_id verification."""
        query = "SELECT * FROM policies WHERE policy_id = ?"
        params: List[Any] = [policy_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            return Policy.model_validate(dict(row))

    def get_policy_by_type(
        self, business_id: str, policy_type: str
    ) -> Optional[Policy]:
        """Retrieve a policy by business_id and policy_type."""
        cleaned_type = policy_type.strip().lower()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM policies WHERE business_id = ? AND policy_type = ?",
                (business_id, cleaned_type),
            ).fetchone()
            if not row:
                return None
            return Policy.model_validate(dict(row))

    def update_policy(
        self,
        policy_id: str,
        data: Union[PolicyUpdate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> Optional[Policy]:
        """Update a policy with tenant isolation."""
        update_model = PolicyUpdate.model_validate(data) if isinstance(data, dict) else data
        update_dict = update_model.model_dump(exclude_unset=True)
        if not update_dict:
            return self.get_policy(policy_id, business_id)

        update_dict["updated_at"] = get_utc_now_iso()
        set_clauses = [f"{k} = ?" for k in update_dict.keys()]
        values = list(update_dict.values()) + [policy_id]

        query = f"UPDATE policies SET {', '.join(set_clauses)} WHERE policy_id = ?"
        if business_id is not None:
            query += " AND business_id = ?"
            values.append(business_id)

        with self._conn() as conn:
            cursor = conn.execute(query, values)
            if cursor.rowcount == 0:
                return None

        return self.get_policy(policy_id, business_id)

    def delete_policy(self, policy_id: str, business_id: Optional[str] = None) -> bool:
        """Delete a policy with optional business verification."""
        query = "DELETE FROM policies WHERE policy_id = ?"
        params: List[Any] = [policy_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def get_policies_by_business(self, business_id: str) -> List[Policy]:
        """Retrieve all policies belonging to a business."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM policies WHERE business_id = ? ORDER BY created_at ASC",
                (business_id,),
            ).fetchall()
            return [Policy.model_validate(dict(row)) for row in rows]

    # =================================================================
    # 5. FAQ CRUD
    # =================================================================

    def create_faq(self, data: Union[FAQCreate, Dict[str, Any]]) -> FAQ:
        """Create a new FAQ entry."""
        create_model = FAQCreate.model_validate(data) if isinstance(data, dict) else data
        now = get_utc_now_iso()
        faq_id = create_model.faq_id or _generate_id("faq")

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO faqs (
                    faq_id, business_id, question, answer, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    faq_id,
                    create_model.business_id,
                    create_model.question,
                    create_model.answer,
                    now,
                    now,
                ),
            )

        return self.get_faq(faq_id, create_model.business_id)  # type: ignore[return-value]

    def get_faq(
        self, faq_id: str, business_id: Optional[str] = None
    ) -> Optional[FAQ]:
        """Retrieve an FAQ by ID with optional business_id verification."""
        query = "SELECT * FROM faqs WHERE faq_id = ?"
        params: List[Any] = [faq_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            return FAQ.model_validate(dict(row))

    def update_faq(
        self,
        faq_id: str,
        data: Union[FAQUpdate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> Optional[FAQ]:
        """Update an FAQ with tenant isolation."""
        update_model = FAQUpdate.model_validate(data) if isinstance(data, dict) else data
        update_dict = update_model.model_dump(exclude_unset=True)
        if not update_dict:
            return self.get_faq(faq_id, business_id)

        update_dict["updated_at"] = get_utc_now_iso()
        set_clauses = [f"{k} = ?" for k in update_dict.keys()]
        values = list(update_dict.values()) + [faq_id]

        query = f"UPDATE faqs SET {', '.join(set_clauses)} WHERE faq_id = ?"
        if business_id is not None:
            query += " AND business_id = ?"
            values.append(business_id)

        with self._conn() as conn:
            cursor = conn.execute(query, values)
            if cursor.rowcount == 0:
                return None

        return self.get_faq(faq_id, business_id)

    def delete_faq(self, faq_id: str, business_id: Optional[str] = None) -> bool:
        """Delete an FAQ with optional business verification."""
        query = "DELETE FROM faqs WHERE faq_id = ?"
        params: List[Any] = [faq_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def get_faqs_by_business(self, business_id: str) -> List[FAQ]:
        """Retrieve all FAQs belonging to a business."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM faqs WHERE business_id = ? ORDER BY created_at ASC",
                (business_id,),
            ).fetchall()
            return [FAQ.model_validate(dict(row)) for row in rows]

    # =================================================================
    # 6. KNOWLEDGE DOCUMENT CRUD
    # =================================================================

    def _row_to_knowledge_document(self, row: sqlite3.Row) -> KnowledgeDocument:
        """Convert a database row to a KnowledgeDocument model with JSON deserialization."""
        d = dict(row)
        d["metadata"] = json.loads(d.get("metadata") or "{}")
        return KnowledgeDocument.model_validate(d)

    def create_knowledge_document(
        self, data: Union[KnowledgeDocumentCreate, Dict[str, Any]]
    ) -> KnowledgeDocument:
        """Create a knowledge document entry for RAG index preparation."""
        create_model = (
            KnowledgeDocumentCreate.model_validate(data)
            if isinstance(data, dict)
            else data
        )
        now = get_utc_now_iso()
        knowledge_id = create_model.knowledge_id or _generate_id("know")
        metadata_json = json.dumps(create_model.metadata or {})

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_documents (
                    knowledge_id, business_id, source_type, source_id,
                    content, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    knowledge_id,
                    create_model.business_id,
                    create_model.source_type,
                    create_model.source_id,
                    create_model.content,
                    metadata_json,
                    now,
                    now,
                ),
            )

        return self.get_knowledge_document(knowledge_id, create_model.business_id)  # type: ignore[return-value]

    def get_knowledge_document(
        self, knowledge_id: str, business_id: Optional[str] = None
    ) -> Optional[KnowledgeDocument]:
        """Retrieve a knowledge document by ID."""
        query = "SELECT * FROM knowledge_documents WHERE knowledge_id = ?"
        params: List[Any] = [knowledge_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            return self._row_to_knowledge_document(row)

    def update_knowledge_document(
        self,
        knowledge_id: str,
        data: Union[KnowledgeDocumentUpdate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> Optional[KnowledgeDocument]:
        """Update a knowledge document."""
        update_model = (
            KnowledgeDocumentUpdate.model_validate(data)
            if isinstance(data, dict)
            else data
        )
        raw_dict = update_model.model_dump(exclude_unset=True)
        if not raw_dict:
            return self.get_knowledge_document(knowledge_id, business_id)

        update_dict: Dict[str, Any] = {}
        for k, v in raw_dict.items():
            if k == "metadata":
                update_dict["metadata"] = json.dumps(v or {})
            else:
                update_dict[k] = v

        update_dict["updated_at"] = get_utc_now_iso()
        set_clauses = [f"{k} = ?" for k in update_dict.keys()]
        values = list(update_dict.values()) + [knowledge_id]

        query = f"UPDATE knowledge_documents SET {', '.join(set_clauses)} WHERE knowledge_id = ?"
        if business_id is not None:
            query += " AND business_id = ?"
            values.append(business_id)

        with self._conn() as conn:
            cursor = conn.execute(query, values)
            if cursor.rowcount == 0:
                return None

        return self.get_knowledge_document(knowledge_id, business_id)

    def delete_knowledge_document(
        self, knowledge_id: str, business_id: Optional[str] = None
    ) -> bool:
        """Delete a knowledge document by ID."""
        query = "DELETE FROM knowledge_documents WHERE knowledge_id = ?"
        params: List[Any] = [knowledge_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def delete_knowledge_documents_by_source(
        self, business_id: str, source_type: str, source_id: str
    ) -> int:
        """Delete all knowledge documents for a specific source entity (useful during updates)."""
        with self._conn() as conn:
            cursor = conn.execute(
                """
                DELETE FROM knowledge_documents
                WHERE business_id = ? AND source_type = ? AND source_id = ?
                """,
                (business_id, source_type, source_id),
            )
            return cursor.rowcount

    def delete_knowledge_documents_by_business(self, business_id: str) -> int:
        """Delete all knowledge documents for a given business (used during full rebuild)."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM knowledge_documents WHERE business_id = ?",
                (business_id,),
            )
            return cursor.rowcount

    def get_knowledge_documents_by_business(
        self, business_id: str
    ) -> List[KnowledgeDocument]:
        """Retrieve all knowledge documents strictly belonging to a business."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM knowledge_documents WHERE business_id = ? ORDER BY created_at ASC",
                (business_id,),
            ).fetchall()
            return [self._row_to_knowledge_document(row) for row in rows]

    def get_knowledge_documents_by_source(
        self, business_id: str, source_type: str, source_id: str
    ) -> List[KnowledgeDocument]:
        """Retrieve knowledge documents matching a specific business and source."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM knowledge_documents
                WHERE business_id = ? AND source_type = ? AND source_id = ?
                ORDER BY created_at ASC
                """,
                (business_id, source_type, source_id),
            ).fetchall()
            return [self._row_to_knowledge_document(row) for row in rows]

    # =================================================================
    # 7. CONVERSATION CRUD
    # =================================================================

    def create_conversation(
        self, data: Union[ConversationCreate, Dict[str, Any]]
    ) -> Conversation:
        """Create a new chat conversation."""
        create_model = (
            ConversationCreate.model_validate(data) if isinstance(data, dict) else data
        )
        now = get_utc_now_iso()
        conversation_id = create_model.conversation_id or _generate_id("conv")

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO conversations (
                    conversation_id, business_id, session_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    create_model.business_id,
                    create_model.session_id,
                    now,
                    now,
                ),
            )

        return self.get_conversation(conversation_id, create_model.business_id)  # type: ignore[return-value]

    def get_conversation(
        self, conversation_id: str, business_id: Optional[str] = None
    ) -> Optional[Conversation]:
        """Retrieve a conversation by ID, optionally verifying business ownership."""
        query = "SELECT * FROM conversations WHERE conversation_id = ?"
        params: List[Any] = [conversation_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            row = conn.execute(query, params).fetchone()
            if not row:
                return None
            return Conversation.model_validate(dict(row))

    def get_conversation_by_session(
        self, business_id: str, session_id: str
    ) -> Optional[Conversation]:
        """Retrieve a conversation for a specific business and session_id."""
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM conversations
                WHERE business_id = ? AND session_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (business_id, session_id),
            ).fetchone()
            if not row:
                return None
            return Conversation.model_validate(dict(row))

    def get_conversations_by_business(self, business_id: str) -> List[Conversation]:
        """Retrieve all conversations for a specific business."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE business_id = ? ORDER BY created_at DESC",
                (business_id,),
            ).fetchall()
            return [Conversation.model_validate(dict(row)) for row in rows]

    def delete_conversation(
        self, conversation_id: str, business_id: Optional[str] = None
    ) -> bool:
        """Delete a conversation (cascades to messages)."""
        query = "DELETE FROM conversations WHERE conversation_id = ?"
        params: List[Any] = [conversation_id]
        if business_id is not None:
            query += " AND business_id = ?"
            params.append(business_id)

        with self._conn() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    # =================================================================
    # 8. MESSAGE CRUD (Tenant-Safe)
    # =================================================================

    def create_message(
        self,
        data: Union[MessageCreate, Dict[str, Any]],
        business_id: Optional[str] = None,
    ) -> Message:
        """Create a new message in a conversation.

        If business_id is provided, enforces that the conversation belongs to that business.
        """
        create_model = MessageCreate.model_validate(data) if isinstance(data, dict) else data
        now = create_model.timestamp or get_utc_now_iso()
        message_id = create_model.message_id or _generate_id("msg")

        with self._conn() as conn:
            if business_id is not None:
                # Verify conversation belongs to business
                conv = conn.execute(
                    "SELECT conversation_id FROM conversations WHERE conversation_id = ? AND business_id = ?",
                    (create_model.conversation_id, business_id),
                ).fetchone()
                if not conv:
                    raise PermissionError(
                        f"Conversation {create_model.conversation_id} does not belong to business {business_id}"
                    )

            conn.execute(
                """
                INSERT INTO messages (
                    message_id, conversation_id, role, content, timestamp
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    create_model.conversation_id,
                    create_model.role,
                    create_model.content,
                    now,
                ),
            )

            row = conn.execute(
                "SELECT * FROM messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            return Message.model_validate(dict(row))

    def get_messages_by_conversation(
        self, conversation_id: str, business_id: Optional[str] = None
    ) -> List[Message]:
        """Retrieve all messages for a conversation ordered by timestamp.

        If business_id is provided, strictly enforces that the conversation belongs
        to that business, preventing cross-tenant message leakages.
        """
        with self._conn() as conn:
            if business_id is not None:
                conv = conn.execute(
                    "SELECT conversation_id FROM conversations WHERE conversation_id = ? AND business_id = ?",
                    (conversation_id, business_id),
                ).fetchone()
                if not conv:
                    # Return empty list if conversation does not belong to this business
                    return []

            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
                (conversation_id,),
            ).fetchall()
            return [Message.model_validate(dict(row)) for row in rows]


# Default singleton instance for easy import across modules
db = DatabaseManager()
