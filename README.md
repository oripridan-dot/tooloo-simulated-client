# tooloo-simulated-client

A **simulated client repository** for testing [TooLoo](https://github.com/oripridan-dot/tooloo-core) end-to-end.

It contains a small FastAPI task-management API (**TaskFlow**) with intentional bugs,
failing tests, and a fully-wired TooLoo MCP bridge server so that TooLoo's agent
swarm can connect, diagnose, and fix the product autonomously.

## Quickstart

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Start the TaskFlow API (port 8001)
uvicorn main:app --reload --port 8001

# 3. Start the MCP bridge server (port 7000, separate terminal)
python product_mcp_server.py

# 4. Run tests (some will fail — intentional)
pytest tests/ -v
```

## Connecting TooLoo

```bash
# In tooloo-core, set the bridge URL and point at this repo
export TOOLOO_MCP_BRIDGE_URL=http://localhost:7000

python TooLoo.py --target ../tooloo-simulated-client
```

## Known Issues (for TooLoo to Fix)

| # | Issue | Location |
|---|-------|----------|
| 1 | `priority` field accepts any string — no enum validation | `routers/tasks.py` |
| 2 | `DELETE /tasks/{id}` returns 200 for non-existent records | `routers/tasks.py` |
| 3 | N+1 anti-pattern in `/users/{id}/tasks` | `routers/users.py` |
| 4 | `updated_at` never populated on PATCH | `routers/tasks.py` |
| 5 | No global exception handler for DB errors | `main.py` |

## MCP Bridge Tools

The `product_mcp_server.py` exposes these tools over JSON-RPC 2.0 at `POST /mcp`:

- `get_project_identity` — project name, stack, `.tooloo.config` contents
- `get_db_schema` — live SQLite schema
- `get_error_logs` — recent `data/error.log` lines
- `get_architecture` — `ARCHITECTURE.md` contents
- `get_source_rules` — `source_rules.md` contents
- `get_directory_structure` — recursive repo tree
- `get_ast_structure` — class/function map for a Python file
- `get_health_status` — git status + recent commits
- `read_file` — read any file in the repo (8 KB cap)

## Project Structure

```
tooloo-simulated-client/
├── main.py                 # FastAPI app
├── database.py             # SQLAlchemy setup
├── models.py               # ORM models
├── routers/
│   ├── tasks.py            # Task CRUD
│   └── users.py            # User CRUD + tasks
├── tests/
│   └── test_tasks.py       # pytest suite (some fail)
├── product_mcp_server.py   # TooLoo MCP bridge
├── .tooloo.config          # Project metadata
├── ARCHITECTURE.md
└── source_rules.md
```
