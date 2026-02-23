# TaskFlow API — Architecture

## Overview

TaskFlow is a lightweight task-management REST API used as a **simulated client**
for TooLoo integration testing. It intentionally contains a number of real-world
bugs that TooLoo's agent swarm should be able to discover, diagnose, and fix.

## Stack

| Layer | Technology |
|-------|-----------|
| API framework | FastAPI |
| Database | SQLite (via SQLAlchemy ORM) |
| Validation | Pydantic v2 |
| Testing | pytest + httpx TestClient |
| MCP bridge | `product_mcp_server.py` (JSON-RPC 2.0 over HTTP) |

## Directory Structure

```
tooloo-simulated-client/
├── main.py                 # FastAPI application entry point
├── database.py             # SQLAlchemy engine, session, Base
├── models.py               # ORM models (User, Task)
├── routers/
│   ├── tasks.py            # CRUD endpoints for tasks
│   └── users.py            # CRUD + user/task relationship
├── tests/
│   └── test_tasks.py       # pytest suite (some tests intentionally fail)
├── product_mcp_server.py   # TooLoo MCP bridge server (port 7000)
├── .tooloo.config          # Project metadata for TooLoo
├── ARCHITECTURE.md         # This document
├── source_rules.md         # Data ownership and coding rules
├── data/
│   └── taskflow.db         # SQLite database (created on first run)
└── pyproject.toml
```

## Data Model

```
User
  id          INTEGER PK
  name        TEXT
  email       TEXT UNIQUE
  created_at  DATETIME

Task
  id          INTEGER PK
  title       TEXT
  description TEXT (nullable)
  priority    TEXT  ← free-text, NO enum constraint (known bug)
  status      TEXT
  owner_id    INTEGER FK → users.id (nullable)
  created_at  DATETIME
  updated_at  DATETIME  ← never populated (known bug)
```

## Known Issues (for TooLoo to Fix)

1. **`priority` has no enum validation** — `TaskCreate.priority` should use
   `Literal["low", "medium", "high"]` or a Pydantic `Enum`.
2. **`DELETE /tasks/{id}` returns 200 for non-existent tasks** — should be 404.
3. **N+1 anti-pattern in `/users/{id}/tasks`** — fetches all tasks then filters
   in Python; should use a SQL WHERE clause.
4. **`updated_at` is never set on PATCH** — the `update_task` handler should
   set `task.updated_at = datetime.utcnow()` before commit.
5. **No global exception handler** — unhandled SQLAlchemy errors surface as
   500 HTML bodies; should return JSON.

## MCP Bridge

TooLoo connects to this product via `product_mcp_server.py` on port 7000.
Set `TOOLOO_MCP_BRIDGE_URL=http://localhost:7000` before running TooLoo against
this repo.

Supported tools: `get_project_identity`, `get_db_schema`, `get_error_logs`,
`get_architecture`, `get_source_rules`, `get_directory_structure`,
`get_ast_structure`, `get_health_status`, `read_file`.
