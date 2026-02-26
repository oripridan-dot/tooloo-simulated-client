"""Test configuration for TaskFlow API.

Uses an in-memory SQLite database so tests are fully isolated and don't
touch the on-disk data/taskflow.db used in development.

Strategy: monkey-patch the `database` module's engine + SessionLocal at
import time (before test_tasks.py creates `client = TestClient(app)`).
SQLite in-memory databases are connection-scoped; use StaticPool so every
session shares the exact same in-memory connection (tables persist).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database  # patch the module in-place

# ── Swap to in-memory engine before anything else touches the DB ──────────────
# StaticPool forces SQLAlchemy to reuse a single underlying connection, which
# guarantees that create_all and all subsequent sessions see the same tables.

_TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)

# Patch module-level singletons so every import of `database` uses the test DB
database.engine = _TEST_ENGINE
database.SessionLocal = _TestingSessionLocal


def _override_get_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Create all tables once for the entire test session ────────────────────────

from database import Base  # noqa: E402  (after patching)
from models import Task, User  # noqa: F401, E402 — register ORM models

Base.metadata.create_all(bind=_TEST_ENGINE)

# Override FastAPI dependency so all HTTP requests use the in-memory DB
from main import app  # noqa: E402
from database import get_db  # noqa: E402

app.dependency_overrides[get_db] = _override_get_db
