"""
Simulated Product: TaskFlow API
================================
A simple FastAPI task-management application.
This repo serves as a reference client for TooLoo integration tests.

Known issues (intentional for TooLoo to discover and fix):
  1. tasks router does NOT validate `priority` enum — accepts any string.
  2. DELETE /tasks/{id} returns 200 even when the task does not exist.
  3. The /users/{id}/tasks endpoint performs a pure Python loop instead
     of a single JOIN query (N+1 anti-pattern).
  4. No global exception handler — unhandled DB errors bubble as 500 HTML.
  5. Missing `updated_at` timestamp on task mutation endpoints.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db
from routers import tasks, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TaskFlow API",
    description="Simulated client for TooLoo integration testing",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "taskflow-api", "version": "0.1.0"}
