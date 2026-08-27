# Phase 9 Regression Diagnosis — SQLite In-Memory State & Test Isolation

**Date**: 2026-08-24  
**Status**: 🔍 **DIAGNOSIS COMPLETE**  
**Current Test Suite State**: 91 / 91 Passing (under isolated filesystem `tmp_path` databases)  
**Diagnosed Regression Scenario**: ~85 test failures when `:memory:` or uninitialized default SQLite state is utilized.

---

## 1. Test Suite Results Summary

### Current Baseline (Filesystem Isolation via `tmp_path`)
- **Total Tests**: 91
- **Passed**: 91
- **Failed**: 0
- **Errors**: 0
- **Skipped**: 0
- **Warnings**: 2 (LangChain deprecation, Starlette TestClient httpx)
- **Execution Time**: ~44.2s

### In-Memory (`:memory:`) Failure Scenario
When `DATABASE_URL="sqlite:///:memory:"` or `DatabaseManager(":memory:")` is used across the suite:
- **Failed / Errored Tests**: ~85 / 91
- **Primary Error**: `sqlite3.OperationalError: no such table: businesses` (and cascading across `products`, `policies`, `faqs`, `assistant_settings`, `conversations`).

---

## 2. Error Grouping & Representative Tracebacks

### Group A: "No Such Table" Due to Connection Lifetime Wiping In-Memory State
```python
Traceback (most recent call last):
  File "core/database.py", line 250, in create_business
    with self._conn() as conn:
  File "core/database.py", line 217, in _conn
    with get_connection(self.db_path) as conn:
  File "contextlib.py", line 144, in __exit__
    next(self.gen)
sqlite3.OperationalError: no such table: businesses
```
- **Affected Subsystems**: `test_database.py`, `test_services.py`, `test_api.py`, `test_rag.py`, `test_retrieval.py`, `test_multi_tenant.py`, `test_seed.py`.

### Group B: `Path(":memory:")` Filesystem Handling
```python
Traceback (most recent call last):
  File "core/database.py", line 176, in create_connection
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path_obj))
```
- `isinstance(Path(":memory:"), Path)` evaluates to `True`, attempting to create a literal file named `:memory:` in the current working directory on Windows rather than opening an in-memory SQLite connection.

### Group C: Global/Default `db` Singleton Uninitialized Schema
When tests or UI modules (`tests/test_ui.py`) import services that rely on `db = DatabaseManager()` without an existing initialized `data/supportbot.db` on disk, unhandled `OperationalError` occurs if `init_db()` has not run.

---

## 3. Root Cause Analysis

### 1. The Per-Operation Connection Lifecycle Pattern
In `core/database.py`:
```python
@contextmanager
def get_connection(db_path=None):
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close() # <--- Connection closed here
```
For file-based SQLite databases (`tmp_path / "test.db"` or `data/supportbot.db`), closing connections per operation is safe, clean, and ensures multi-threaded WAL concurrency.

However, for standard SQLite `:memory:` databases:
1. `init_db(":memory:")` opens Connection 1, creates all 8 tables, and closes Connection 1. **SQLite immediately purges the entire in-memory database upon closing the connection.**
2. The next operation `db.create_business(...)` opens Connection 2. Connection 2 is a brand-new, empty in-memory database with **zero tables**.
3. It throws `no such table: businesses`.

### 2. Ambiguity Between `Path` and `str` for `:memory:`
- `core/config.py` returns `Path(":memory:")` for `sqlite:///:memory:`.
- `core/database.py` checks `if isinstance(target_path, Path) or (isinstance(target_path, str) and target_path != ":memory:"):`.
- Because `Path(":memory:")` is an instance of `Path`, it bypasses the string check and treats `:memory:` as a disk filename.

### 3. WAL Mode on In-Memory Databases
- `PRAGMA journal_mode = WAL;` is executed on every connection. In-memory databases do not support WAL mode (returns `memory` or fails silently), causing unnecessary pragma overhead.

---

## 4. Architectural Comparison & Best Practices

| Strategy | Advantages | Drawbacks | Recommended? |
| :--- | :--- | :--- | :---: |
| **Anonymous `:memory:` with Per-Call Connect** | Fast | Wiped on every `conn.close()`; impossible to use with context managers without a persistent connection holder. | ❌ No |
| **Shared URI Memory Cache (`file:memdb?mode=memory&cache=shared`)** | In-memory, survives across connections as long as 1 connection remains open. | Complex locking on Windows; can cause concurrency deadlocks during parallel tests. | ⚠️ Complex |
| **Isolated Temporary File (`tmp_path / "*.db"`)** | 100% clean isolation per test; supports WAL mode, multi-threading, foreign keys, and automatic OS cleanup. | Minor disk I/O (negligible for small test suites). | ✅ **Best Practice (Current)** |

---

## 5. Files Responsible

1. `core/database.py`:
   - `create_connection`: Needs robust `:memory:` detection (`str(target_path) == ":memory:"`).
   - `create_connection`: Skip `PRAGMA journal_mode = WAL;` when connected to `:memory:`.
   - `DatabaseManager`: Support optional persistent connection or auto-schema initialization if used with in-memory databases.
2. `core/config.py`:
   - `database_path`: Return `":memory:"` as `str` or handle `Path(":memory:")` cleanly.
3. `tests/test_embed_integration.py`:
   - Ensure all API endpoints in tests use isolated `DatabaseManager(tmp_path / "...")` via dependency injection rather than relying on global state.
4. `tests/test_ui.py`:
   - Ensure `init_db()` is guaranteed before `AppTest` runs.

---

## 6. Proposed Minimal Fix

1. **Update `core/database.py`**:
   - Normalize `db_path` in `resolve_db_path`: If `str(p) == ":memory:"`, return `":memory:"` as a string.
   - In `create_connection`:
     ```python
     is_memory = str(target_path) == ":memory:" or (isinstance(target_path, str) and target_path.startswith("file:") and "mode=memory" in target_path)
     if not is_memory:
         path_obj = Path(target_path)
         path_obj.parent.mkdir(parents=True, exist_ok=True)
         conn = sqlite3.connect(str(path_obj))
         conn.execute("PRAGMA journal_mode = WAL;")
     else:
         conn = sqlite3.connect(target_path if isinstance(target_path, str) else ":memory:", check_same_thread=False)
     ```
   - In `DatabaseManager.initialize()`: Ensure `init_db(self.db_path)` is called safely.
2. **Update `core/config.py`**:
   - Ensure `database_path` returns `Path(raw_path)` for file paths and `":memory:"` string for memory targets.
3. **Preserve Isolated File Fixtures in Tests**:
   - All tests in `tests/` will continue using `tmp_path` (e.g. `tmp_path / "test.db"`), guaranteeing 100% deterministic test isolation, zero cross-test interference, and clean teardown.

---

## 7. Risks & Mitigations

- **Risk**: Affecting production SQLite persistence.
  - *Mitigation*: Production uses `sqlite:///data/supportbot.db` which is file-based and fully validated. The change only enhances path normalization and in-memory safety.
- **Risk**: Evaluation dataset contamination.
  - *Mitigation*: Evaluation tests use mock retrieval and read-only fixtures, verified by SHA-256 hash checks.
