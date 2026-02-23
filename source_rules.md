# Source & Data Ownership Rules

## Code Ownership

| File / Directory         | Owner Agent / Team          | Notes |
|--------------------------|-----------------------------|-------|
| `main.py`                | Platform team               | Lifespan & router registration only |
| `database.py`            | Platform team               | Schema must match `models.py` exactly |
| `models.py`              | Data team                   | Any schema change requires a migration |
| `routers/tasks.py`       | Tasks squad                 | Pydantic schemas must stay in-file |
| `routers/users.py`       | Users squad                 | |
| `product_mcp_server.py`  | TooLoo auto-generated       | Do NOT edit manually |
| `tests/`                 | QA / TooLoo                 | Test file must remain `tests/test_tasks.py` |

## Coding Rules

1. **All API responses must be Pydantic models** — never return raw SQLAlchemy objects.
2. **Priority values** must be one of `["low", "medium", "high"]` — validate at schema level.
3. **All mutation endpoints** (`POST`, `PATCH`, `PUT`, `DELETE`) must set `updated_at`
   on affected models.
4. **Database queries** must filter at the SQL level — Python-side filtering is forbidden.
5. **All HTTP errors** must use `HTTPException` and return JSON bodies.
6. **No direct `db.execute()` calls** — use SQLAlchemy ORM query API only.
7. **Test coverage** must remain ≥ 80 % for `routers/`.

## Data Rules

- The SQLite database is stored at `data/taskflow.db` — do not move it.
- `data/` is git-ignored (runtime artefacts).
- `email` is unique per user — enforce at both DB constraint and API level.
- Soft-delete is not implemented — `DELETE` is a hard delete.
