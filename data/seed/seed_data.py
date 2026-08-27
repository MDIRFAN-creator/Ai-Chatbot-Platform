"""Seed Data Automation Pipeline for SupportBot AI.

Populates SQLite with realistic business data fixtures (UrbanThreads)
and optionally generates the production FAISS vector store with local embeddings.

Usage:
    python data/seed/seed_data.py [--force] [--rebuild-knowledge] [--db-path PATH]
    python -m data.seed.seed_data
"""

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.database import DatabaseManager, init_db
from core.models import (
    AssistantSettingsCreate,
    BusinessCreate,
    FAQCreate,
    PolicyCreate,
    ProductCreate,
)
from knowledge.knowledge_manager import KnowledgeManager

logger = logging.getLogger("supportbot.seed")
SEED_DIR = Path(__file__).resolve().parent / "urbanthreads"


def load_fixture(filename: str) -> Any:
    """Load and parse a JSON fixture file from the urbanthreads seed directory."""
    fixture_path = SEED_DIR / filename
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_path}")
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_urbanthreads(
    db: Optional[DatabaseManager] = None,
    rebuild_knowledge: bool = True,
    force: bool = False,
) -> str:
    """Seed the UrbanThreads sample merchant records into the database.

    Args:
        db: Optional DatabaseManager instance; defaults to global database.
        rebuild_knowledge: If True, builds/rebuilds the FAISS vector index.
        force: If True, deletes any existing UrbanThreads tenant before inserting.

    Returns:
        business_id of the seeded merchant ("urbanthreads_001").
    """
    if db is None:
        init_db()
        db = DatabaseManager()

    business_data = load_fixture("business.json")
    biz_info = business_data["business"]
    asst_info = business_data["assistant_settings"]
    business_id = biz_info["business_id"]

    existing = db.get_business(business_id)
    if existing:
        if force:
            logger.info(f"Force flag set: Deleting existing tenant '{business_id}'...")
            db.delete_business(business_id)
        else:
            logger.info(f"Tenant '{business_id}' already exists. Skipping fixture insert.")
            if rebuild_knowledge:
                km = KnowledgeManager(db_manager=db)
                km.build_knowledge_base(business_id=business_id)
            return business_id

    # 1. Create Business
    logger.info(f"Creating business '{biz_info['name']}' ({business_id})...")
    db.create_business(
        BusinessCreate(
            business_id=business_id,
            name=biz_info["name"],
            description=biz_info.get("description"),
            industry=biz_info.get("industry"),
            website=biz_info.get("website"),
            contact_email=biz_info.get("contact_email"),
            contact_phone=biz_info.get("contact_phone"),
            location=biz_info.get("location"),
        )
    )

    # 2. Create Assistant Settings
    logger.info(f"Creating assistant settings for '{business_id}'...")
    db.create_or_update_assistant_settings(
        AssistantSettingsCreate(
            business_id=business_id,
            assistant_name=asst_info.get("assistant_name", "UrbanThreads Assistant"),
            tone=asst_info.get("tone", "friendly and professional"),
            welcome_message=asst_info.get("welcome_message"),
        )
    )

    # 3. Create Products
    products = load_fixture("products.json")
    logger.info(f"Inserting {len(products)} products...")
    for prod in products:
        db.create_product(
            ProductCreate(
                product_id=prod.get("product_id"),
                business_id=business_id,
                name=prod["name"],
                description=prod.get("description"),
                price=prod.get("price"),
                currency=prod.get("currency", "INR"),
                category=prod.get("category"),
                sizes=prod.get("sizes", []),
                colors=prod.get("colors", []),
                availability=prod.get("availability", "in_stock"),
                returnable=prod.get("returnable", True),
                product_url=prod.get("product_url"),
            )
        )

    # 4. Create Policies
    policies = load_fixture("policies.json")
    logger.info(f"Inserting {len(policies)} policies...")
    for pol in policies:
        db.create_policy(
            PolicyCreate(
                business_id=business_id,
                policy_type=pol["policy_type"],
                content=pol["content"],
            )
        )

    # 5. Create FAQs
    faqs = load_fixture("faqs.json")
    logger.info(f"Inserting {len(faqs)} FAQs...")
    for faq in faqs:
        db.create_faq(
            FAQCreate(
                business_id=business_id,
                question=faq["question"],
                answer=faq["answer"],
            )
        )

    # 6. Build Knowledge Base & FAISS Index
    if rebuild_knowledge:
        logger.info(f"Generating FAISS vector index and normalized documents for '{business_id}'...")
        km = KnowledgeManager(db_manager=db)
        summary = km.build_knowledge_base(business_id=business_id)
        doc_count = summary.get("normalized_documents_count", 0)
        logger.info(f"Knowledge base successfully built with {doc_count} LangChain documents.")

    logger.info(f"Successfully seeded '{business_id}'!")
    return business_id


def main() -> None:
    """CLI entrypoint for seeding sample data."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="SupportBot AI Seed Data CLI")
    parser.add_argument("--force", action="store_true", help="Overwrite existing tenant records")
    parser.add_argument(
        "--no-knowledge",
        action="store_true",
        help="Skip automatic FAISS vector index generation",
    )
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite database file path")

    args = parser.parse_args()

    db_path = Path(args.db_path) if args.db_path else None
    if db_path:
        init_db(db_path)
        db = DatabaseManager(db_path)
    else:
        init_db()
        db = DatabaseManager()

    seed_urbanthreads(
        db=db,
        rebuild_knowledge=not args.no_knowledge,
        force=args.force,
    )
    print("\n[SUCCESS] Seed complete: UrbanThreads records and vector store are ready!")


if __name__ == "__main__":
    main()
