# UrbanThreads Seed Data & Fixtures

This directory contains structured JSON fixtures representing the **UrbanThreads** reference merchant for development, benchmarking, and demonstrations.

---

## 1. Fixture Inventory

- `business.json` — Business profile, contact information, and initial AI assistant configuration.
- `products.json` — Product catalog (Hoodies, Jackets, Graphic Tees, Pants) including prices, sizes, colors, and returnability flags.
- `policies.json` — Complete merchant policies: Shipping, Returns, Refunds, Payment methods, and Sizing.
- `faqs.json` — Storefront FAQs covering order tracking, international delivery, care instructions, and cancellations.

---

## 2. One-Command Seeding

To seed the SQLite database and automatically generate the local Sentence-Transformers FAISS vector index:

```powershell
.venv\Scripts\python.exe data/seed/seed_data.py --force
```

Or via module execution:
```powershell
.venv\Scripts\python.exe -m data.seed.seed_data
```

### CLI Flags
- `--force`: Overwrites any existing `urbanthreads_001` records.
- `--no-knowledge`: Inserts SQLite records without rebuilding the FAISS index.
- `--db-path <PATH>`: Seeds a custom SQLite database file.
